"""Shared helpers for Django TestCase suites."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from agents.models import Agent, Booking
from calls.models import CallLog

User = get_user_model()


def create_user(email="test@example.com", password="testpass123", **extra):
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        **extra,
    )


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_agent(user, name="Test Agent", retell_agent_id="agent_test_123", **extra):
    defaults = {
        "owner": user,
        "agent_name": name,
        "retell_agent_id": retell_agent_id,
        "status": "live",
        "system_prompt": "You are a helpful agent.",
        "language": "en-US",
    }
    defaults.update(extra)
    return Agent.objects.create(**defaults)


def make_call(agent, call_sid="call_test_sid_1", **extra):
    defaults = {
        "agent": agent,
        "twilio_call_sid": call_sid,
        "direction": "web_call",
        "status": "completed",
        "duration_seconds": 60,
        "caller_phone": "",
    }
    defaults.update(extra)
    return CallLog.objects.create(**defaults)


def make_booking(agent, booking_type="table", guest_name="Guest One", **extra):
    from datetime import date, timedelta

    defaults = {
        "agent": agent,
        "booking_type": booking_type,
        "guest_name": guest_name,
        "guest_email": "guest@example.com",
        "guest_phone": "+15551212",
        "guests": 2,
        "check_in": date.today() + timedelta(days=1),
        "is_confirmed": False,
    }
    defaults.update(extra)
    return Booking.objects.create(**defaults)


def extract_list_items(body):
    """Unwrap paginated success_response envelopes used by list APIs.

    Typical shape from Pagination + success_response:
      { count, next, previous, results: { success, message, data: [ ... ] } }
    Also handles plain { success, data: [...] } and DRF { results: [...] }.
    """
    if not isinstance(body, dict):
        return body if isinstance(body, list) else []

    # Paginated: results holds the success envelope
    results = body.get("results")
    if isinstance(results, dict) and "data" in results:
        data = results.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data["results"]
    if isinstance(results, list):
        return results

    data = body.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested = data.get("results")
        if isinstance(nested, list):
            return nested
        if isinstance(nested, dict) and isinstance(nested.get("data"), list):
            return nested["data"]
    return []
