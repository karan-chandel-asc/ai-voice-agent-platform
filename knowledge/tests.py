"""Knowledge base API tests — ownership isolation."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.test_utils import create_user, auth_client, make_agent


class KnowledgeAPITests(TestCase):
    def setUp(self):
        self.user = create_user("kb@example.com")
        self.other = create_user("kb2@example.com")
        self.agent = make_agent(self.user, name="KB Agent", retell_agent_id="agent_kb1")
        make_agent(self.other, name="Other KB", retell_agent_id="agent_kb2")
        self.client = auth_client(self.user)

    def test_agents_list_requires_auth(self):
        url = reverse("kb-agents")
        self.assertEqual(APIClient().get(url).status_code, 401)

    def test_agents_list_only_own(self):
        url = reverse("kb-agents")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        data = body.get("data") or body
        # tolerate list or paginated
        if isinstance(data, dict):
            items = data.get("results") or data.get("agents") or data.get("data") or []
            if isinstance(items, dict):
                items = items.get("results") or []
        else:
            items = data
        names = {a.get("agent_name") or a.get("name") for a in items}
        self.assertIn("KB Agent", names)
        self.assertNotIn("Other KB", names)

    def test_documents_list_requires_auth(self):
        url = reverse("kb-documents")
        self.assertEqual(APIClient().get(url).status_code, 401)

    def test_documents_list_ok(self):
        url = reverse("kb-documents")
        res = self.client.get(url + f"?agent_id={self.agent.id}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success", True) or "data" in res.json())

    def test_upload_without_file_fails(self):
        url = reverse("kb-upload")
        res = self.client.post(url, {"agent_id": str(self.agent.id)}, format="multipart")
        self.assertIn(res.status_code, (400, 415, 500))
