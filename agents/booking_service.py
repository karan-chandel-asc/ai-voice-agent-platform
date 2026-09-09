"""Local booking writes — no external webhooks."""
import os
from datetime import datetime, date as date_cls, timedelta


def _ensure_django():
    import django
    from django.apps import apps
    if apps.ready:
        return
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


def _int(val, default=1):
    try:
        return max(1, int(val))
    except (TypeError, ValueError):
        return default


def _resolve_agent(agent_id=None, call_sid=None):
    if not agent_id and not call_sid:
        return None
    from django.core.exceptions import ValidationError as DjangoValidationError
    from agents.models import Agent
    from calls.models import CallLog

    if agent_id:
        rid = str(agent_id).strip()
        if rid.startswith("agent_"):
            hit = Agent.objects.filter(retell_agent_id=rid).first()
            if hit:
                return hit
        else:
            try:
                return Agent.objects.get(id=rid)
            except (Agent.DoesNotExist, ValueError, TypeError, DjangoValidationError):
                pass
            hit = Agent.objects.filter(retell_agent_id=rid).first()
            if hit:
                return hit

    sid = (call_sid or "").strip()
    if sid:
        log = CallLog.objects.select_related("agent").filter(twilio_call_sid=sid).first()
        if log and log.agent_id:
            return log.agent
    return None


def _parse_date(raw: str):
    raw = str(raw).strip().lower()
    if raw == "today":
        return date_cls.today()
    if raw in ("tomorrow", "tommorrow"):
        return date_cls.today() + timedelta(days=1)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("Invalid date format. Use YYYY-MM-DD.")


def save_room_booking(data: dict) -> dict:
    _ensure_django()
    from agents.models import Booking

    required = ["guest_name", "email", "check_in_date", "check_out_date"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return {"success": False, "message": f"Missing fields: {', '.join(missing)}"}

    try:
        check_in_obj = _parse_date(data["check_in_date"])
        check_out_obj = _parse_date(data["check_out_date"])
    except ValueError as e:
        return {"success": False, "message": str(e)}

    if check_out_obj <= check_in_obj:
        return {"success": False, "message": "Check-out must be after check-in."}

    nights = (check_out_obj - check_in_obj).days
    call_sid = data.get("call_sid", "") or ""

    booking = Booking.objects.create(
        agent=_resolve_agent(data.get("agent_id"), call_sid),
        call_sid=call_sid,
        booking_type="room",
        guest_name=data["guest_name"],
        guest_email=data.get("email", "") or "",
        guests=_int(data.get("guests", 1), 1),
        check_in=check_in_obj,
        check_out=check_out_obj,
        is_confirmed=False,
    )

    return {
        "success": True,
        "message": (
            f"Room booking request saved for {booking.guest_name}, "
            f"check-in {check_in_obj.strftime('%B %d')}, check-out {check_out_obj.strftime('%B %d')}, "
            f"{nights} night{'s' if nights != 1 else ''}, {booking.guests} guest(s). "
            f"Status is pending until staff confirms it."
        ),
    }


def save_table_booking(data: dict) -> dict:
    _ensure_django()
    from agents.models import Booking

    # Accept date or check_in_date for the reservation day
    raw_date = data.get("date") or data.get("check_in_date")
    required_missing = []
    if not data.get("guest_name"):
        required_missing.append("guest_name")
    if not raw_date:
        required_missing.append("date")
    if not data.get("guests"):
        required_missing.append("guests")
    if required_missing:
        return {"success": False, "message": f"Missing fields: {', '.join(required_missing)}"}

    try:
        date_obj = _parse_date(raw_date)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    call_sid = data.get("call_sid", "") or ""
    booking = Booking.objects.create(
        agent=_resolve_agent(data.get("agent_id"), call_sid),
        call_sid=call_sid,
        booking_type="table",
        guest_name=data["guest_name"],
        guest_email=data.get("guest_email", "") or data.get("email", "") or "",
        guests=_int(data.get("guests")),
        check_in=date_obj,
        check_out=None,
        is_confirmed=False,
    )

    return {
        "success": True,
        "message": (
            f"Table booking request saved for {booking.guest_name}, party of {booking.guests} "
            f"on {date_obj.strftime('%A, %B %d')}. "
            f"Status is pending until staff confirms it."
        ),
    }
