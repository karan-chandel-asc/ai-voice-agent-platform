from .models import CustomUser


class UserService:

    def check_email_exists(self, email):
        try:
            exists = CustomUser.objects.filter(email=email).exists()
            if exists:
                return True, "Email already exists"
            return False, None
        except Exception as e:
            return None, f"Error comes while checking email: {e}"

    def login_user(self, email, password):
        try:
            from django.contrib.auth import authenticate
            user = authenticate(username=email, password=password)
            if not user:
                return None, "Invalid credentials"
            return user, None
        except Exception as e:
            return None, f"Error during login: {e}"

    def get_google_redirect_url(self, redirect_uri):
        try:
            import urllib.parse
            from django.conf import settings
            params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
            }
            return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params), None
        except Exception as e:
            return None, str(e)

    def exchange_google_code(self, code, redirect_uri):
        try:
            import requests as req
            from django.conf import settings
            token_res = req.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            tokens = token_res.json()
            if "error" in tokens:
                return None, tokens.get("error_description", "Google OAuth failed")

            user_res = req.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            info = user_res.json()
            email = info.get("email")
            first_name = info.get("given_name", "")
            last_name = info.get("family_name", "")

            if not email:
                return None, "Could not retrieve email from Google"

            user = CustomUser.objects.filter(email=email).first()
            if not user:
                if CustomUser.objects.exists():
                    return None, "This desk already has an account. Please sign in."
                user = CustomUser.objects.create_user(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                )
            return user, None
        except Exception as e:
            return None, f"Google authentication failed: {e}"

    def generate_reset_token(self, email):
        try:
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.contrib.auth.tokens import default_token_generator
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                return None, None
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            return uid, token
        except Exception:
            return None, None

    def reset_password(self, uid, token, password):
        try:
            from django.utils.http import urlsafe_base64_decode
            from django.utils.encoding import force_str
            from django.contrib.auth.tokens import default_token_generator
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
            if not default_token_generator.check_token(user, token):
                return None, "Invalid or expired reset link"
            user.set_password(password)
            user.save()
            return user, None
        except Exception as e:
            return None, f"Error resetting password: {e}"

    def create_user(self, data):
        try:
            if CustomUser.objects.exists():
                return None, "Only one operator account is allowed. Please sign in."
            user = CustomUser.objects.create_user(
                username=data.work_email,
                email=data.work_email,
                password=data.password,
                first_name=data.first_name,
                last_name=data.last_name,
                business_name=data.business_name,
            )
            return user, None
        except Exception as e:
            return None, f"Error comes while creating user: {e}"
