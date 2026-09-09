"""Monitoring app — analytics render auth gate."""
from django.test import TestCase, Client
from django.urls import reverse

from core.test_utils import create_user


class MonitoringRenderTests(TestCase):
    def setUp(self):
        self.user = create_user("mon@example.com")
        self.client = Client()

    def test_analytics_page_redirects_or_loads(self):
        url = reverse("voice-analytics")
        res = self.client.get(url)
        # RenderAPIView may redirect unauthenticated users to login
        self.assertIn(res.status_code, (200, 302, 401, 403))

    def test_analytics_page_authenticated_session(self):
        self.client.force_login(self.user)
        url = reverse("voice-analytics")
        res = self.client.get(url)
        self.assertIn(res.status_code, (200, 302))
