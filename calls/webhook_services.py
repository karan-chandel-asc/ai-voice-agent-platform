"""Handle Retell webhooks: call_started, call_ended, call_analyzed."""
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from core.logger import logger
from .models import CallLog, CallTranscript

LOG = "[RETELL WEBHOOK]"


def _ms_to_dt(ms):
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000.0, tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _resolve_agent(retell_agent_id: str):
    if not retell_agent_id:
        return None
    from agents.models import Agent
    rid = str(retell_agent_id).strip()
    agent = Agent.objects.filter(retell_agent_id=rid).first()
    if agent:
        return agent
    # Retell sometimes sends id without prefix / with extra whitespace variants
    return Agent.objects.filter(retell_agent_id__icontains=rid).first()


def _direction(call: dict) -> str:
    """No Retell direction → web call; otherwise inbound (no outbound in this flow)."""
    d = (call.get("direction") or "").strip()
    if not d:
        return "web_call"
    return "inbound"


def _caller_phone(call: dict) -> str:
    phone = call.get("from_number") or call.get("to_number") or ""
    phone = str(phone).strip()
    return phone[:20] if phone else ""


def _map_ended_status(call: dict) -> str:
    reason = (call.get("disconnection_reason") or "").lower()
    status = (call.get("call_status") or "").lower()
    if "error" in reason or status in ("error", "failed"):
        return "failed"
    if "transfer" in reason:
        return "transferred"
    if "no_answer" in reason or "not_connected" in reason or "busy" in reason:
        return "no-answer"
    return "completed"


def _sentiment_label(analysis: dict) -> str:
    """Retell sends user_sentiment as Positive / Negative / Neutral."""
    if not analysis:
        return ""
    raw = str(
        analysis.get("user_sentiment")
        or analysis.get("sentiment")
        or ""
    ).strip().lower()
    if "positive" in raw:
        return "positive"
    if "negative" in raw:
        return "negative"
    if "neutral" in raw:
        return "neutral"
    return ""


def _apply_call_analysis(log: CallLog, call: dict) -> bool:
    """Map Retell call.call_analysis → CallLog fields. Returns True if anything applied."""
    analysis = call.get("call_analysis")
    if not isinstance(analysis, dict) or not analysis:
        logger.info(f"{LOG} analysis skip — call_analysis missing or empty")
        return False

    changed = False
    label = _sentiment_label(analysis)
    if label:
        log.sentiment_score = label
        changed = True
        logger.info(f"{LOG} analysis sentiment={label}")

    summary = (analysis.get("call_summary") or analysis.get("summary") or "").strip()
    if summary:
        log.reason = summary[:100]
        changed = True
        logger.info(f"{LOG} analysis summary saved ({len(summary)} chars)")

    if not changed:
        logger.info(f"{LOG} analysis present but no sentiment/summary to store")
    return changed


def _duration_seconds(call: dict) -> int:
    if call.get("total_duration_seconds") is not None:
        try:
            return int(call["total_duration_seconds"])
        except (TypeError, ValueError):
            pass
    start = call.get("start_timestamp")
    end = call.get("end_timestamp")
    if start and end:
        try:
            return max(0, int(round((int(end) - int(start)) / 1000)))
        except (TypeError, ValueError):
            pass
    return 0


def _turn_offset_seconds(turn: dict, fallback_index: int) -> float:
    """Best-effort start time for a Retell transcript turn (seconds into call)."""
    words = turn.get("words")
    if isinstance(words, list) and words:
        first = words[0] if isinstance(words[0], dict) else None
        if first and first.get("start") is not None:
            try:
                return max(0.0, float(first["start"]))
            except (TypeError, ValueError):
                pass

    for key in ("start", "start_sec", "time_sec", "offset_ms", "start_timestamp"):
        if turn.get(key) is None:
            continue
        try:
            val = float(turn[key])
            if key == "offset_ms" or (key == "start_timestamp" and val > 10_000):
                return max(0.0, val / 1000.0)
            return max(0.0, val)
        except (TypeError, ValueError):
            continue

    # Estimate from spoken length (~12 chars/sec) with a floor of 2s per turn gap
    content = (turn.get("content") or "").strip()
    estimated = max(2.0, min(12.0, len(content) / 12.0))
    return float(fallback_index) * estimated


def _save_transcripts(call_log: CallLog, call: dict) -> int:
    objects = call.get("transcript_object") or []
    if not isinstance(objects, list) or not objects:
        text = (call.get("transcript") or "").strip()
        if not text:
            logger.info(f"{LOG} transcript skip — no transcript_object or transcript text")
            return 0
        CallTranscript.objects.filter(call=call_log).delete()
        CallTranscript.objects.create(
            call=call_log,
            speaker="agent",
            text=text,
            timestamp=call_log.ended_at or call_log.started_at or timezone.now(),
        )
        logger.info(f"{LOG} transcript saved as single blob ({len(text)} chars)")
        return 1

    CallTranscript.objects.filter(call=call_log).delete()
    base_ts = call_log.started_at or timezone.now()
    rows = []
    turn_i = 0
    last_offset = -1.0
    for turn in objects:
        if not isinstance(turn, dict):
            continue
        role = (turn.get("role") or "").lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "agent":
            speaker = "agent"
        elif role == "user":
            speaker = "caller"
        else:
            continue

        offset = _turn_offset_seconds(turn, turn_i)
        # Keep timestamps strictly increasing when Retell omits per-turn times
        if offset <= last_offset:
            offset = last_offset + 2.0
        last_offset = offset
        turn_i += 1

        rows.append(CallTranscript(
            call=call_log,
            speaker=speaker,
            text=content,
            timestamp=base_ts + timedelta(seconds=offset),
            langgraph_node=str(turn.get("tool_call_id") or "")[:50],
        ))
    if rows:
        CallTranscript.objects.bulk_create(rows)
        logger.info(f"{LOG} transcript saved — {len(rows)} turns")
        return len(rows)

    logger.info(f"{LOG} transcript skip — no agent/user turns with content")
    return 0


@transaction.atomic
def handle_call_started(call: dict) -> dict:
    """Only persist Retell call_id; full details come on call_ended."""
    call_id = (call.get("call_id") or "").strip()
    logger.info(f"{LOG} ▶ call_started begin call_id={call_id or '(missing)'}")

    if not call_id:
        logger.warning(f"{LOG} ✖ call_started failed — call_id missing in payload")
        return {"ok": False, "message": "call_id missing"}

    log, created = CallLog.objects.get_or_create(
        twilio_call_sid=call_id,
        defaults={"status": "in-progress"},
    )
    if created:
        logger.info(f"{LOG} ✓ call_started NEW CallLog created id={log.id} status=in-progress")
    else:
        if log.status != "completed":
            log.status = "in-progress"
            log.save(update_fields=["status"])
            logger.info(
                f"{LOG} ✓ call_started existing CallLog id={log.id} "
                f"— already had this call_id, set status=in-progress"
            )
        else:
            logger.info(
                f"{LOG} ✓ call_started existing CallLog id={log.id} "
                f"— already completed, left status unchanged"
            )

    return {
        "ok": True,
        "message": "Call id stored" if created else "Call id already stored",
        "call_id": call_id,
        "id": str(log.id),
    }


@transaction.atomic
def handle_call_ended(call: dict) -> dict:
    call_id = (call.get("call_id") or "").strip()
    retell_agent_id = call.get("agent_id") or ""
    logger.info(
        f"{LOG} ▶ call_ended begin call_id={call_id or '(missing)'} "
        f"retell_agent_id={retell_agent_id or '(none)'}"
    )

    if not call_id:
        logger.warning(f"{LOG} ✖ call_ended failed — call_id missing in payload")
        return {"ok": False, "message": "call_id missing"}

    agent = _resolve_agent(retell_agent_id)
    if agent:
        logger.info(f"{LOG} agent matched name={agent.agent_name} db_id={agent.id}")
    else:
        logger.warning(
            f"{LOG} agent not found for retell_agent_id={retell_agent_id or '(empty)'} "
            f"— CallLog will have no agent link"
        )

    log = CallLog.objects.select_for_update().filter(twilio_call_sid=call_id).first()
    if not log:
        log = CallLog.objects.create(
            agent=agent,
            twilio_call_sid=call_id,
            status="in-progress",
            started_at=_ms_to_dt(call.get("start_timestamp")) or timezone.now(),
        )
        logger.warning(
            f"{LOG} call_ended arrived BEFORE call_started — "
            f"created CallLog now id={log.id}"
        )
    else:
        logger.info(f"{LOG} found CallLog from call_started id={log.id}")

    if agent and log.agent_id != getattr(agent, "id", None):
        log.agent = agent
        logger.info(f"{LOG} linked agent onto CallLog")

    phone = _caller_phone(call)
    if phone:
        log.caller_phone = phone
    else:
        logger.info(f"{LOG} no phone number in payload (likely web call)")

    log.direction = _direction(call)
    log.status = _map_ended_status(call)
    log.duration_seconds = _duration_seconds(call)
    log.recording_url = (call.get("recording_url") or call.get("public_log_url") or "")[:200]
    log.reason = (call.get("disconnection_reason") or log.reason or "")[:100]
    log.was_transferred = "transfer" in (call.get("disconnection_reason") or "").lower()

    if not log.started_at:
        log.started_at = _ms_to_dt(call.get("start_timestamp"))
    log.ended_at = _ms_to_dt(call.get("end_timestamp")) or timezone.now()

    logger.info(
        f"{LOG} call_ended fields → direction={log.direction} status={log.status} "
        f"duration={log.duration_seconds}s phone={log.caller_phone or '(empty)'} "
        f"disconnect={log.reason or '(none)'} recording={'yes' if log.recording_url else 'no'}"
    )

    _apply_call_analysis(log, call)
    log.save()
    turns = _save_transcripts(log, call)

    logger.info(
        f"{LOG} ✓ call_ended saved CallLog id={log.id} call_id={call_id} "
        f"status={log.status} transcript_turns={turns}"
    )
    return {"ok": True, "message": "Call ended stored", "call_id": call_id, "id": str(log.id)}


@transaction.atomic
def handle_call_analyzed(call: dict) -> dict:
    """Only read call.call_analysis and write sentiment/summary onto CallLog."""
    call_id = (call.get("call_id") or "").strip()
    logger.info(f"{LOG} ▶ call_analyzed begin call_id={call_id or '(missing)'}")

    if not call_id:
        logger.warning(f"{LOG} ✖ call_analyzed failed — call_id missing in payload")
        return {"ok": False, "message": "call_id missing"}

    log, created = CallLog.objects.select_for_update().get_or_create(
        twilio_call_sid=call_id,
        defaults={"status": "in-progress"},
    )
    if created:
        logger.warning(
            f"{LOG} call_analyzed arrived with no prior CallLog — "
            f"created row id={log.id}"
        )
    else:
        logger.info(f"{LOG} found CallLog id={log.id} for analysis")

    if not _apply_call_analysis(log, call):
        logger.info(f"{LOG} ✓ call_analyzed done — nothing new to store call_id={call_id}")
        return {"ok": True, "message": "No call_analysis to store", "call_id": call_id, "id": str(log.id)}

    log.save()
    logger.info(
        f"{LOG} ✓ call_analyzed saved CallLog id={log.id} "
        f"sentiment={log.sentiment_score or '(none)'} "
        f"summary={'yes' if log.reason else 'no'}"
    )
    return {"ok": True, "message": "Call analysis stored", "call_id": call_id, "id": str(log.id)}


def process_retell_webhook(payload: dict) -> dict:
    event = (payload.get("event") or "").strip()
    call = payload.get("call") if isinstance(payload.get("call"), dict) else {}
    call_id = (call.get("call_id") or "").strip() if call else ""

    logger.info(f"{LOG} ── route event={event or '(missing)'} call_id={call_id or '(none)'} ──")

    if not event:
        logger.warning(f"{LOG} ✖ reject — event field missing in webhook body")
        return {"ok": False, "message": "event missing"}

    if event == "call_started":
        return handle_call_started(call)

    if event == "call_ended":
        return handle_call_ended(call)

    if event == "call_analyzed":
        return handle_call_analyzed(call)

    logger.info(f"{LOG} ignore unsupported event={event} (only started/ended/analyzed handled)")
    return {"ok": True, "message": f"Ignored event {event}"}
