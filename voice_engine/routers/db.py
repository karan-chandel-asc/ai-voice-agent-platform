"""
DB access for the voice engine via Django ORM (works with SQLite or Postgres).
No Docker / asyncpg required for local runs.
"""
import os
from asgiref.sync import sync_to_async


def _ensure_django():
    import django
    from django.apps import apps
    if apps.ready:
        return
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


def _agent_payload(agent) -> dict:
    voice_id = None
    if agent.elevenlabs_voice_id:
        voice_id = getattr(agent.elevenlabs_voice, "voice_id", None)

    tools = []
    for link in agent.user_tools.filter(is_active=True).select_related("user_tool"):
        ut = link.user_tool
        if not ut.is_active:
            continue
        tools.append({
            "id": str(ut.id),
            "name": ut.name,
            "description": ut.description,
            "parameters": ut.parameters or {},
        })

    kb_doc_ids = []
    try:
        from knowledge.models import AgentDocument
        kb_doc_ids = [
            str(d.id)
            for d in AgentDocument.objects.filter(agent=agent, status="ready").only("id")
        ]
    except Exception:
        kb_doc_ids = []

    return {
        "agent_id": str(agent.id),
        "agent_name": agent.agent_name,
        "system_prompt": agent.system_prompt or "",
        "status": agent.status,
        "language": agent.language or "en",
        "elevenlabs_voice_id": voice_id,
        "tools": [],
        "user_tools": tools,
        "kb_doc_ids": kb_doc_ids,
    }


def _get_demo_agent_sync() -> dict | None:
    _ensure_django()
    from agents.models import Agent
    agent = (
        Agent.objects.filter(is_demo=True, status="live")
        .select_related("elevenlabs_voice")
        .first()
    )
    return _agent_payload(agent) if agent else None


def _get_live_agents_sync() -> list[dict]:
    _ensure_django()
    from agents.models import Agent
    agents = (
        Agent.objects.filter(status="live")
        .select_related("elevenlabs_voice")
        .order_by("agent_name")
    )
    return [
        {"agent_id": str(a.id), "agent_name": a.agent_name}
        for a in agents
    ]


def _get_agent_by_id_sync(agent_id: str) -> dict | None:
    _ensure_django()
    from agents.models import Agent
    try:
        agent = (
            Agent.objects.filter(id=agent_id, status="live")
            .select_related("elevenlabs_voice")
            .prefetch_related("user_tools__user_tool")
            .get()
        )
    except (Agent.DoesNotExist, ValueError, TypeError):
        return None
    return _agent_payload(agent)


def _get_agent_by_phone_sync(to_number: str) -> dict | None:
    _ensure_django()
    from agents.models import Agent
    agent = (
        Agent.objects.filter(phone_number=to_number, status="live")
        .select_related("elevenlabs_voice")
        .prefetch_related("user_tools__user_tool")
        .first()
    )
    return _agent_payload(agent) if agent else None


def _create_call_log_sync(call_sid: str, from_number: str, agent_id: str | None = None) -> None:
    _ensure_django()
    from calls.models import CallLog
    from agents.models import Agent

    agent = None
    if agent_id:
        try:
            agent = Agent.objects.filter(id=agent_id).first()
        except (ValueError, TypeError):
            agent = None

    CallLog.objects.get_or_create(
        twilio_call_sid=call_sid,
        defaults={
            "caller_phone": from_number or "",
            "agent": agent,
            "direction": "inbound",
            "status": "initiated",
            "outcome": "no_outcome",
            "duration_seconds": 0,
            "was_transferred": False,
            "recording_url": "",
            "reason": "",
        },
    )


def _update_call_log_sync(call_sid: str, **fields) -> None:
    _ensure_django()
    from django.utils import timezone
    from calls.models import CallLog

    ALLOWED = {
        "status", "duration_seconds", "outcome", "sentiment_score",
        "was_transferred", "recording_url", "reason",
    }
    safe = {k: v for k, v in fields.items() if k in ALLOWED}
    set_ended_at = fields.get("ended_at", False)
    if not safe and not set_ended_at:
        return
    if set_ended_at:
        safe["ended_at"] = timezone.now()
    CallLog.objects.filter(twilio_call_sid=call_sid).update(**safe)


def _save_transcript_sync(call_sid: str, speaker: str, text: str) -> None:
    _ensure_django()
    from django.utils import timezone
    from calls.models import CallLog, CallTranscript

    call = CallLog.objects.filter(twilio_call_sid=call_sid).first()
    if not call:
        return
    CallTranscript.objects.create(
        call=call,
        speaker=speaker,
        text=text,
        langgraph_node="",
        timestamp=timezone.now(),
    )


# ── Async wrappers ─────────────────────────────────────────────────────────────
async def get_demo_agent() -> dict | None:
    return await sync_to_async(_get_demo_agent_sync, thread_sensitive=True)()


async def get_live_agents() -> list[dict]:
    return await sync_to_async(_get_live_agents_sync, thread_sensitive=True)()


async def get_agent_by_id(agent_id: str) -> dict | None:
    return await sync_to_async(_get_agent_by_id_sync, thread_sensitive=True)(agent_id)


async def get_agent_by_phone(to_number: str) -> dict | None:
    return await sync_to_async(_get_agent_by_phone_sync, thread_sensitive=True)(to_number)


async def create_call_log(call_sid: str, from_number: str, agent_id: str | None = None) -> None:
    await sync_to_async(_create_call_log_sync, thread_sensitive=True)(call_sid, from_number, agent_id)


async def update_call_log(call_sid: str, **fields) -> None:
    await sync_to_async(_update_call_log_sync, thread_sensitive=True)(call_sid, **fields)


async def save_transcript(call_sid: str, speaker: str, text: str) -> None:
    await sync_to_async(_save_transcript_sync, thread_sensitive=True)(call_sid, speaker, text)
