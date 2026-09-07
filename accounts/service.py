from .models import CustomUser


class UserService:
    """Business logic for auth and password reset.

    Keeps views thin by handling credential checks
    and Django token encode/decode helpers.
    """

    def login_user(self, email, password):
        """Authenticate by email and password.

        Returns (user, None) on success.
        Returns (None, error_message) on failure.
        """
        try:
            from django.contrib.auth import authenticate
            user = authenticate(username=email, password=password)
            if not user:
                return None, "Invalid credentials"
            return user, None
        except Exception as e:
            return None, f"Error during login: {e}"

    def generate_reset_token(self, email):
        """Build a password-reset uid and token.

        Looks up the user by email first.
        Returns (None, None) when the email is unknown.
        """
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
        """Apply a new password after token validation.

        Decodes uid and checks the Django reset token.
        Returns (user, None) or (None, error_message).
        """
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
