from datetime import date as date_cls, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db.models import Q

ROOM_TYPES = ("Deluxe Room", "Superior Room", "Family Room")

# Demo inventory + nightly rates (USD) for the property
ROOM_INVENTORY = {
    "Deluxe Room": 8,
    "Superior Room": 6,
    "Family Room": 4,
}
ROOM_RATES = {
    "Deluxe Room": Decimal("180.00"),
    "Superior Room": Decimal("240.00"),
    "Family Room": Decimal("320.00"),
}
TAX_RATE = Decimal("0.12")


def parse_date(raw) -> date_cls:
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


def normalize_room_type(room_type: str) -> str:
    cleaned = (room_type or "").strip()
    for allowed in ROOM_TYPES:
        if cleaned.lower() == allowed.lower():
            return allowed
    raise ValueError(
        "room_type must be one of: Deluxe Room, Superior Room, or Family Room."
    )


def _int(val, default=1) -> int:
    try:
        return max(1, int(val))
    except (TypeError, ValueError):
        return default


def resolve_agent(agent_id=None, phone_number=None, call_sid=None):
    from agents.models import Agent, RetellPhoneNumber
    from calls.models import CallLog

    if agent_id:
        rid = str(agent_id).strip()
        try:
            return Agent.objects.get(id=rid)
        except (Agent.DoesNotExist, ValueError, TypeError):
            pass
        # Retell tools often send retell agent id, not our UUID
        hit = Agent.objects.filter(retell_agent_id=rid).first()
        if hit:
            return hit

    sid = (call_sid or "").strip()
    if sid:
        log = CallLog.objects.select_related("agent").filter(twilio_call_sid=sid).first()
        if log and log.agent_id:
            return log.agent

    phone = (phone_number or "").strip()
    if phone:
        hit = RetellPhoneNumber.objects.filter(
            Q(phone_number=phone) | Q(phone_number_pretty=phone),
            assigned_agent__isnull=False,
        ).select_related("assigned_agent").first()
        if hit:
            return hit.assigned_agent
        return Agent.objects.filter(phone_number=phone).first()
    return None


def _overlapping_count(room_type: str, check_in: date_cls, check_out: date_cls, agent=None) -> int:
    from agents.models import Booking

    qs = Booking.objects.filter(
        booking_type="room",
        room_type=room_type,
        check_in__lt=check_out,
        check_out__gt=check_in,
    )
    if agent:
        qs = qs.filter(agent=agent)
    return qs.count()


def check_room_availability(
    *,
    check_in_date: str,
    check_out_date: str,
    number_of_guests: int,
    agent_id=None,
    agent_phone=None,
) -> dict:
    check_in = parse_date(check_in_date)
    check_out = parse_date(check_out_date)
    if check_out <= check_in:
        return {"success": False, "message": "Check-out must be after check-in.", "data": None}

    guests = _int(number_of_guests, 1)
    nights = (check_out - check_in).days
    agent = resolve_agent(agent_id, agent_phone)

    rooms = []
    for room_type, capacity in ROOM_INVENTORY.items():
        booked = _overlapping_count(room_type, check_in, check_out, agent)
        available = max(0, capacity - booked)
        # Family Room preferred for 3+ guests; others cap soft-warn only
        guest_ok = True
        if room_type == "Family Room" and guests > 5:
            guest_ok = False
        elif room_type != "Family Room" and guests > 3:
            guest_ok = False
        rooms.append({
            "room_type": room_type,
            "available_count": available,
            "is_available": available > 0 and guest_ok,
            "nightly_rate": float(ROOM_RATES[room_type]),
            "guest_fit": guest_ok,
        })

    any_available = any(r["is_available"] for r in rooms)
    return {
        "success": True,
        "message": (
            f"Availability for {check_in.isoformat()} to {check_out.isoformat()} "
            f"({nights} night{'s' if nights != 1 else ''}, {guests} guest(s))."
        ),
        "data": {
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "nights": nights,
            "number_of_guests": guests,
            "rooms": rooms,
            "has_availability": any_available,
        },
    }


def calculate_booking_price(
    *,
    room_type: str,
    check_in_date: str,
    check_out_date: str,
    number_of_guests: int,
) -> dict:
    try:
        room = normalize_room_type(room_type)
    except ValueError as e:
        return {"success": False, "message": str(e), "data": None}

    check_in = parse_date(check_in_date)
    check_out = parse_date(check_out_date)
    if check_out <= check_in:
        return {"success": False, "message": "Check-out must be after check-in.", "data": None}

    guests = _int(number_of_guests, 1)
    nights = (check_out - check_in).days
    nightly = ROOM_RATES[room]
    room_charges = (nightly * nights).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxes = (room_charges * TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (room_charges + taxes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "success": True,
        "message": f"Price calculated for {room}: {nights} night(s), total ${total}.",
        "data": {
            "room_type": room,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "number_of_guests": guests,
            "nights": nights,
            "nightly_rate": float(nightly),
            "room_charges": float(room_charges),
            "taxes": float(taxes),
            "tax_rate": float(TAX_RATE),
            "total": float(total),
            "currency": "USD",
        },
    }


def create_room_reservation(data: dict) -> dict:
    from agents.models import Booking

    required = [
        "guest_name", "phone_number", "email", "check_in_date",
        "check_out_date", "number_of_guests", "room_type",
    ]
    missing = [f for f in required if data.get(f) in (None, "")]
    if missing:
        return {"success": False, "message": f"Missing fields: {', '.join(missing)}", "data": None}

    email = str(data.get("email") or "").strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"success": False, "message": "A valid email address is required.", "data": None}

    try:
        room = normalize_room_type(data["room_type"])
        check_in = parse_date(data["check_in_date"])
        check_out = parse_date(data["check_out_date"])
    except ValueError as e:
        return {"success": False, "message": str(e), "data": None}

    if check_out <= check_in:
        return {"success": False, "message": "Check-out must be after check-in.", "data": None}

    guests = _int(data.get("number_of_guests"), 1)
    call_sid = data.get("call_sid") or data.get("call_id") or ""
    agent = resolve_agent(
        data.get("agent_id"),
        data.get("agent_phone") or data.get("to_number"),
        call_sid=call_sid,
    )
    nights = (check_out - check_in).days

    avail = check_room_availability(
        check_in_date=check_in.isoformat(),
        check_out_date=check_out.isoformat(),
        number_of_guests=guests,
        agent_id=getattr(agent, "id", None),
    )
    room_row = next((r for r in (avail.get("data") or {}).get("rooms", []) if r["room_type"] == room), None)
    if not room_row or not room_row["is_available"]:
        return {
            "success": False,
            "message": f"{room} is not available for the selected dates.",
            "data": avail.get("data"),
        }

    price = calculate_booking_price(
        room_type=room,
        check_in_date=check_in.isoformat(),
        check_out_date=check_out.isoformat(),
        number_of_guests=guests,
    )
    price_data = price.get("data") or {}

    booking = Booking.objects.create(
        agent=agent,
        call_sid=call_sid,
        booking_type="room",
        guest_name=str(data["guest_name"]).strip(),
        guest_email=email,
        guest_phone=str(data["phone_number"]).strip(),
        guests=guests,
        room_type=room,
        special_requests=(data.get("special_requests") or "").strip(),
        nights=nights,
        total_price=Decimal(str(price_data.get("total") or 0)),
        check_in=check_in,
        check_out=check_out,
        is_confirmed=False,
    )

    return {
        "success": True,
        "message": (
            f"Reservation request saved for {booking.guest_name} — {room}, "
            f"{check_in.isoformat()} to {check_out.isoformat()}, "
            f"{nights} night(s), total ${price_data.get('total', 0)}. "
            f"Status is pending until the hotel confirms it."
        ),
        "data": {
            "booking_id": str(booking.id),
            "guest_name": booking.guest_name,
            "phone_number": booking.guest_phone,
            "email": booking.guest_email,
            "room_type": booking.room_type,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "number_of_guests": guests,
            "nights": nights,
            "total_price": float(booking.total_price or 0),
            "special_requests": booking.special_requests,
            "is_confirmed": booking.is_confirmed,
            "status": "pending",
        },
    }
