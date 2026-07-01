from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from .models import Integration

User = get_user_model()


def create_user(email="test@example.com", password="testpass123"):
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
    )


def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# ── IntegrationListView ────────────────────────────────────────────────────────

class IntegrationListViewTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = auth_client(self.user)
        self.url = reverse("integration-status")

    def test_unauthenticated_returns_401(self):
        res = APIClient().get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_returns_200_for_authenticated_user(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_response_has_success_true(self):
        res = self.client.get(self.url)
        self.assertTrue(res.json()["success"])

    def test_auto_creates_integration_rows_for_all_types(self):
        res = self.client.get(self.url)
        data = res.json()["data"]
        types_returned = {i["type"] for i in data}
        expected = {t for t, _ in Integration.TYPE_CHOICES}
        self.assertEqual(types_returned, expected)

    def test_returns_only_current_users_integrations(self):
        other = create_user("other@example.com")
        Integration.objects.create(user=other, type="google_sheets", is_connected=True)
        res = self.client.get(self.url)
        for item in res.json()["data"]:
            obj = Integration.objects.get(id=item["id"])
            self.assertEqual(obj.user, self.user)

    def test_new_integrations_default_to_not_connected(self):
        res = self.client.get(self.url)
        for item in res.json()["data"]:
            self.assertFalse(item["is_connected"])


# ── IntegrationToggleView ──────────────────────────────────────────────────────

class IntegrationToggleViewTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = auth_client(self.user)
        self.url = reverse("integration-toggle")

    def test_unauthenticated_returns_401(self):
        res = APIClient().post(self.url, {"type": "google_sheets", "connect": True}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_connect_google_sheets_returns_200(self):
        res = self.client.post(self.url, {"type": "google_sheets", "connect": True}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_connect_sets_is_connected_true(self):
        self.client.post(self.url, {"type": "google_sheets", "connect": True}, format="json")
        obj = Integration.objects.get(user=self.user, type="google_sheets")
        self.assertTrue(obj.is_connected)

    def test_connect_sets_connected_at_timestamp(self):
        self.client.post(self.url, {"type": "google_sheets", "connect": True}, format="json")
        obj = Integration.objects.get(user=self.user, type="google_sheets")
        self.assertIsNotNone(obj.connected_at)

    def test_disconnect_sets_is_connected_false(self):
        Integration.objects.create(user=self.user, type="google_sheets", is_connected=True)
        self.client.post(self.url, {"type": "google_sheets", "connect": False}, format="json")
        obj = Integration.objects.get(user=self.user, type="google_sheets")
        self.assertFalse(obj.is_connected)

    def test_disconnect_clears_connected_at(self):
        Integration.objects.create(user=self.user, type="google_sheets", is_connected=True)
        self.client.post(self.url, {"type": "google_sheets", "connect": False}, format="json")
        obj = Integration.objects.get(user=self.user, type="google_sheets")
        self.assertIsNone(obj.connected_at)

    def test_invalid_type_returns_400(self):
        res = self.client.post(self.url, {"type": "invalid_type", "connect": True}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_missing_type_returns_400(self):
        res = self.client.post(self.url, {"connect": True}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_response_contains_integration_data(self):
        res = self.client.post(self.url, {"type": "google_sheets", "connect": True}, format="json")
        data = res.json()["data"]
        self.assertIn("type", data)
        self.assertIn("is_connected", data)
        self.assertEqual(data["type"], "google_sheets")
        self.assertTrue(data["is_connected"])

    def test_toggle_does_not_affect_other_users_integration(self):
        other = create_user("other@example.com")
        Integration.objects.create(user=other, type="google_sheets", is_connected=False)
        self.client.post(self.url, {"type": "google_sheets", "connect": True}, format="json")
        other_obj = Integration.objects.get(user=other, type="google_sheets")
        self.assertFalse(other_obj.is_connected)


# ── send_daily_call_report task ────────────────────────────────────────────────

class SendDailyCallReportTaskTests(TestCase):

    def setUp(self):
        self.user = create_user("report@example.com")
        Integration.objects.create(user=self.user, type="google_sheets", is_connected=True)

    @patch("integrations.tasks.EmailMessage.send")
    def test_task_sends_email_to_connected_user(self, mock_send):
        from integrations.tasks import send_daily_call_report
        send_daily_call_report()
        mock_send.assert_called_once()

    @patch("integrations.tasks.EmailMessage.send")
    def test_task_does_not_send_to_disconnected_user(self, mock_send):
        Integration.objects.filter(user=self.user).update(is_connected=False)
        from integrations.tasks import send_daily_call_report
        send_daily_call_report()
        mock_send.assert_not_called()

    @patch("integrations.tasks.EmailMessage.send", side_effect=Exception("SMTP error"))
    def test_task_does_not_crash_on_email_failure(self, mock_send):
        from integrations.tasks import send_daily_call_report
        try:
            send_daily_call_report()
        except Exception:
            self.fail("send_daily_call_report raised an exception on email failure")

    @patch("integrations.tasks.EmailMessage.send")
    def test_task_sends_to_multiple_connected_users(self, mock_send):
        user2 = create_user("user2@example.com")
        Integration.objects.create(user=user2, type="google_sheets", is_connected=True)
        from integrations.tasks import send_daily_call_report
        send_daily_call_report()
        self.assertEqual(mock_send.call_count, 2)
