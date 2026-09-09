"""Agents app tests — list/CRUD isolation, tools, resolve_agent, web call."""
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from agents.models import Booking
from agents import tool_services
from core.test_utils import create_user, auth_client, make_agent, make_call, extract_list_items


class AgentListIsolationTests(TestCase):
    def setUp(self):
        self.user = create_user("owner@example.com")
        self.other = create_user("other@example.com")
        self.agent = make_agent(self.user, name="Mine", retell_agent_id="agent_mine")
        make_agent(self.other, name="Theirs", retell_agent_id="agent_theirs")
        self.client = auth_client(self.user)
        self.url = reverse("agent-list")

    def test_list_requires_auth(self):
        self.assertEqual(APIClient().get(self.url).status_code, 401)

    def test_list_only_own_agents(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        results = extract_list_items(res.json())
        names = {a.get("agent_name") for a in results}
        self.assertIn("Mine", names)
        self.assertNotIn("Theirs", names)

    def test_get_own_agent(self):
        url = reverse("agent-crud", kwargs={"pk": str(self.agent.id)})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_get_foreign_agent_404(self):
        foreign = make_agent(self.other, name="X", retell_agent_id="agent_x2")
        url = reverse("agent-crud", kwargs={"pk": str(foreign.id)})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_delete_does_not_remove_retell(self):
        url = reverse("agent-delete", kwargs={"pk": str(self.agent.id)})
        with patch("agents.services.retell_services.delete_retell_agent") as mock_del:
            res = self.client.delete(url)
            self.assertEqual(res.status_code, 200)
            mock_del.assert_not_called()
        self.assertFalse(type(self.agent).objects.filter(id=self.agent.id).exists())


class ResolveAgentTests(TestCase):
    def setUp(self):
        self.user = create_user("r@example.com")
        self.agent = make_agent(self.user, retell_agent_id="agent_abc123")

    def test_resolve_by_retell_id(self):
        hit = tool_services.resolve_agent(agent_id="agent_abc123")
        self.assertEqual(hit.id, self.agent.id)

    def test_resolve_by_uuid(self):
        hit = tool_services.resolve_agent(agent_id=str(self.agent.id))
        self.assertEqual(hit.id, self.agent.id)

    def test_resolve_by_call_sid(self):
        make_call(self.agent, call_sid="call_resolve_1")
        hit = tool_services.resolve_agent(call_sid="call_resolve_1")
        self.assertEqual(hit.id, self.agent.id)

    def test_invalid_retell_id_does_not_500(self):
        hit = tool_services.resolve_agent(agent_id="agent_missing_zzz")
        self.assertIsNone(hit)


class RoomToolTests(TestCase):
    def setUp(self):
        self.user = create_user("tools@example.com")
        self.agent = make_agent(self.user, retell_agent_id="agent_hotel_1")
        self.client = APIClient()  # tools are AllowAny

    def test_check_room_availability(self):
        url = reverse("tool-check-room-availability")
        check_in = (date.today() + timedelta(days=3)).isoformat()
        check_out = (date.today() + timedelta(days=5)).isoformat()
        res = self.client.post(
            url,
            {"check_in_date": check_in, "check_out_date": check_out, "number_of_guests": 2},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])
        self.assertIn("rooms", res.json()["data"])

    def test_check_room_with_retell_wrapper(self):
        url = reverse("tool-check-room-availability")
        check_in = (date.today() + timedelta(days=3)).isoformat()
        check_out = (date.today() + timedelta(days=5)).isoformat()
        res = self.client.post(
            url,
            {
                "args": {
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "number_of_guests": 2,
                },
                "call": {"call_id": "call_wrap_1", "agent_id": "agent_hotel_1"},
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["success"])

    def test_check_room_missing_fields(self):
        url = reverse("tool-check-room-availability")
        res = self.client.post(url, {"check_in_date": "2026-01-01"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_calculate_booking_price(self):
        url = reverse("tool-calculate-booking-price")
        check_in = (date.today() + timedelta(days=3)).isoformat()
        check_out = (date.today() + timedelta(days=5)).isoformat()
        res = self.client.post(
            url,
            {
                "room_type": "Deluxe Room",
                "check_in_date": check_in,
                "check_out_date": check_out,
                "number_of_guests": 2,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])
        self.assertIn("total", res.json()["data"])

    def test_create_room_reservation(self):
        url = reverse("tool-create-room-reservation")
        check_in = (date.today() + timedelta(days=10)).isoformat()
        check_out = (date.today() + timedelta(days=12)).isoformat()
        res = self.client.post(
            url,
            {
                "args": {
                    "guest_name": "Alice Room",
                    "phone_number": "+15550001",
                    "email": "alice@example.com",
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "number_of_guests": 2,
                    "room_type": "Deluxe Room",
                },
                "call": {"call_id": "call_room_create", "agent_id": "agent_hotel_1"},
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["success"])
        b = Booking.objects.get(guest_name="Alice Room")
        self.assertEqual(b.booking_type, "room")
        self.assertEqual(b.agent_id, self.agent.id)


class TableToolTests(TestCase):
    def setUp(self):
        self.user = create_user("table@example.com")
        self.agent = make_agent(self.user, retell_agent_id="agent_rest_1")
        self.client = APIClient()

    def test_check_table_availability(self):
        url = reverse("tool-check-table-availability")
        day = (date.today() + timedelta(days=2)).isoformat()
        res = self.client.post(
            url,
            {"reservation_date": day, "reservation_time": "19:30", "number_of_guests": 2},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["data"]["is_available"])

    def test_create_table_reservation(self):
        url = reverse("tool-create-table-reservation")
        day = (date.today() + timedelta(days=4)).isoformat()
        res = self.client.post(
            url,
            {
                "args": {
                    "guest_name": "Bob Table",
                    "phone_number": "+15550002",
                    "email": "bob@example.com",
                    "reservation_date": day,
                    "reservation_time": "20:00",
                    "number_of_guests": 3,
                    "special_requests": "Window",
                },
                "call": {"call_id": "call_table_1", "agent_id": "agent_rest_1"},
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["success"])
        b = Booking.objects.get(guest_name="Bob Table")
        self.assertEqual(b.booking_type, "table")
        self.assertEqual(b.agent_id, self.agent.id)
        self.assertIsNotNone(b.reservation_date_time)


class CreateWebCallAPITests(TestCase):
    def setUp(self):
        self.user = create_user("web@example.com")
        self.agent = make_agent(self.user, retell_agent_id="agent_web_1")
        self.client = auth_client(self.user)

    @patch("agents.views.retell_services.create_web_call")
    def test_create_web_call(self, mock_create):
        mock_create.return_value = (
            {"call_id": "call_w1", "access_token": "tok_abc", "agent_id": "agent_web_1"},
            "Web call created",
        )
        url = reverse("agent-create-web-call", kwargs={"pk": str(self.agent.id)})
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["data"]["access_token"], "tok_abc")

    def test_web_call_requires_retell_id(self):
        bare = make_agent(self.user, name="Local", retell_agent_id="")
        url = reverse("agent-create-web-call", kwargs={"pk": str(bare.id)})
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, 400)
