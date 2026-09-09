"""Accounts app tests — auth, profile, logout."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.test_utils import create_user, auth_client


class LoginAPITests(TestCase):
    def setUp(self):
        self.user = create_user("login@example.com", "Secret123!")
        self.url = reverse("login-api")

    def test_login_success(self):
        res = APIClient().post(
            self.url,
            {"email": "login@example.com", "password": "Secret123!"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get("success"))
        data = body.get("data") or body
        # access token may be nested or top-level depending on view shape
        token = data.get("access") or (data.get("tokens") or {}).get("access")
        self.assertTrue(token or "access" in str(body))

    def test_login_wrong_password(self):
        res = APIClient().post(
            self.url,
            {"email": "login@example.com", "password": "wrong"},
            format="json",
        )
        self.assertIn(res.status_code, (400, 401))

    def test_login_missing_fields(self):
        res = APIClient().post(self.url, {}, format="json")
        self.assertIn(res.status_code, (400, 401))


class ProfileAPITests(TestCase):
    def setUp(self):
        self.user = create_user("profile@example.com", business_name="Grand Harbor")
        self.client = auth_client(self.user)
        self.url = reverse("user-profile")

    def test_profile_requires_auth(self):
        res = APIClient().get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_profile_get(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get("success"))
        data = body.get("data") or {}
        self.assertEqual(data.get("email"), "profile@example.com")

    def test_profile_update(self):
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "business_name": "Updated Hotel",
            "phone": "+15550001",
        }
        res = self.client.put(self.url, payload, format="json")
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.business_name, "Updated Hotel")
        self.assertEqual(self.user.phone, "+15550001")


class LogoutAPITests(TestCase):
    def setUp(self):
        self.user = create_user("logout@example.com")
        self.client = auth_client(self.user)
        self.url = reverse("logout")

    def test_logout(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = str(RefreshToken.for_user(self.user))
        res = self.client.post(self.url, {"refresh": refresh}, format="json")
        self.assertIn(res.status_code, (200, 205))
