"""Calls app tests — Retell webhook lifecycle + call history isolation."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from calls.models import CallLog, CallTranscript
from core.test_utils import create_user, auth_client, make_agent, make_call, extract_list_items


class RetellWebhookTests(TestCase):
    def setUp(self):
        self.user = create_user("calls@example.com")
        self.agent = make_agent(self.user, retell_agent_id="agent_wh_1")
        self.client = APIClient()
        self.url = reverse("retell-call-webhook")

    def test_call_started_creates_log(self):
        res = self.client.post(
            self.url,
            {
                "event": "call_started",
                "call": {
                    "call_id": "call_started_1",
                    "agent_id": "agent_wh_1",
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        log = CallLog.objects.get(twilio_call_sid="call_started_1")
        self.assertEqual(log.status, "in-progress")
        self.assertEqual(log.agent_id, self.agent.id)

    def test_call_ended_updates_fields(self):
        CallLog.objects.create(
            twilio_call_sid="call_ended_1",
            agent=self.agent,
            status="in-progress",
        )
        res = self.client.post(
            self.url,
            {
                "event": "call_ended",
                "call": {
                    "call_id": "call_ended_1",
                    "agent_id": "agent_wh_1",
                    "call_status": "ended",
                    "start_timestamp": 1_700_000_000_000,
                    "end_timestamp": 1_700_000_090_000,
                    "transcript_object": [
                        {"role": "agent", "content": "Hello"},
                        {"role": "user", "content": "Hi there"},
                    ],
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        log = CallLog.objects.get(twilio_call_sid="call_ended_1")
        self.assertEqual(log.status, "completed")
        self.assertEqual(log.direction, "web_call")
        self.assertGreaterEqual(CallTranscript.objects.filter(call=log).count(), 1)

    def test_call_analyzed_sets_sentiment(self):
        CallLog.objects.create(
            twilio_call_sid="call_an_1",
            agent=self.agent,
            status="completed",
        )
        res = self.client.post(
            self.url,
            {
                "event": "call_analyzed",
                "call": {
                    "call_id": "call_an_1",
                    "call_analysis": {
                        "user_sentiment": "Positive",
                        "call_summary": "Guest booked a room.",
                    },
                },
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        log = CallLog.objects.get(twilio_call_sid="call_an_1")
        self.assertEqual(log.sentiment_score, "positive")

    def test_missing_event_rejected(self):
        res = self.client.post(self.url, {"call": {"call_id": "x"}}, format="json")
        self.assertEqual(res.status_code, 400)


class CallHistoryAPITests(TestCase):
    def setUp(self):
        self.user = create_user("hist@example.com")
        self.other = create_user("hist2@example.com")
        self.agent = make_agent(self.user, retell_agent_id="agent_h1")
        other_agent = make_agent(self.other, retell_agent_id="agent_h2")
        self.mine = make_call(self.agent, call_sid="call_mine_1")
        make_call(other_agent, call_sid="call_other_1")
        self.client = auth_client(self.user)
        self.url = reverse("call-history-list")

    def test_requires_auth(self):
        self.assertEqual(APIClient().get(self.url).status_code, 401)

    def test_list_only_own_calls(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        results = extract_list_items(res.json())
        sids = {c.get("twilio_call_sid") for c in results}
        self.assertIn("call_mine_1", sids)
        self.assertNotIn("call_other_1", sids)

    def test_detail_own_call(self):
        url = reverse("call-history-detail", kwargs={"pk": self.mine.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_bulk_delete_own_calls(self):
        url = reverse("call-history-bulk-delete")
        res = self.client.post(url, {"ids": [str(self.mine.id)]}, format="json")
        # Some views use DELETE with body
        if res.status_code == 405:
            res = self.client.delete(url, {"ids": [str(self.mine.id)]}, format="json")
        self.assertIn(res.status_code, (200, 204))
        self.assertFalse(CallLog.objects.filter(id=self.mine.id).exists())
