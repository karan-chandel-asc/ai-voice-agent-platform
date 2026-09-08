from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from pydantic import ValidationError

from .schemas import LoginViewSchema, ForgotPasswordSchema, ResetPasswordSchema
from .service import UserService
from .tasks import send_password_reset_email
from core.logger import logger
from core.response_schemas import success_response, error_response
from django.shortcuts import render


service = UserService()


class LoginRender(APIView):
    """Serve the email/password login page.

    Public GET endpoint with no auth required.
    Renders voice_login.html for the console.
    """

    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        """Return the login HTML page."""
        logger.info("Request received for login Get Method")
        return render(request, 'voice_login.html')


class LoginAPIView(APIView):
    """Authenticate a user and issue JWT tokens.

    Accepts email and password in the request body.
    Sets an access_token cookie on success.
    """

    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        """Validate credentials and return access/refresh tokens."""
        try:
            logger.info("Request received for login Post Method")
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
            next_url = request.data.get('next', None)

            try:
                validated_data = LoginViewSchema(**data)
            except ValidationError as e:
                err = e.errors()[0]
                message = err['msg'].replace('Value error, ', '')
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            user, err = service.login_user(validated_data.email, validated_data.password)
            if not user:
                return Response(error_response(message=err), status=status.HTTP_400_BAD_REQUEST)

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            response = Response(success_response(
                message="Login successful",
                data={
                    "access": access_token,
                    "refresh": str(refresh),
                }
            ), status=status.HTTP_200_OK)
            response.set_cookie('access_token', access_token, samesite='Lax', httponly=False)
            return response

        except Exception as e:
            logger.error(f"Login error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """Blacklist the refresh token and clear session cookie.

    Expects a refresh token in the POST body.
    Always deletes the access_token cookie on success.
    """

    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        """Invalidate refresh token and clear auth cookie."""
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(error_response(message="Refresh token is required."), status=status.HTTP_400_BAD_REQUEST)
        try:
            logger.info("Request comes for user logout")
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return Response(error_response(message="Invalid or expired token."), status=status.HTTP_400_BAD_REQUEST)

        response = Response(success_response(message="Logged out successfully"), status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        return response


class ForgotPasswordRender(APIView):
    """Serve the forgot-password request page.

    Public GET endpoint with no auth required.
    Renders voice_forgot_password.html.
    """

    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        """Return the forgot-password HTML page."""
        logger.info("Request received for forgot password Render Html")
        return render(request, 'voice_forgot_password.html')


class ForgotPasswordView(APIView):
    """Start a password reset for a registered email.

    Always returns a generic success message.
    Sends a reset link via Celery when the user exists.
    """

    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        """Validate email and queue a password-reset email."""
        try:
            logger.info("Request comes for forgot password")
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
            try:
                schema = ForgotPasswordSchema(**data)
            except ValidationError as e:
                err     = e.errors()[0]
                message = err['msg'].replace('Value error, ', '')
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            uid, token = service.generate_reset_token(schema.email)

            if uid and token:
                reset_url = f"{request.scheme}://{request.get_host()}/api/auth/reset-password/?uid={uid}&token={token}"
                send_password_reset_email.delay(schema.email, reset_url)

            return Response(
                success_response(message="If this email is registered, a reset link has been sent."),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Forgot password error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordRender(APIView):
    """Serve the reset-password form page.

    Public GET endpoint with no auth required.
    Renders ase_reset_password.html.
    """

    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        """Return the reset-password HTML page."""
        logger.info("GET Request received for reset password page")
        return render(request, 'ase_reset_password.html')


class ResetPasswordAPIView(APIView):
    """Set a new password using a valid reset token.

    Requires uid, token, and new password in the body.
    Rejects invalid or expired reset links.
    """

    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        """Validate reset payload and update the user password."""
        try:
            logger.info("Request comes for reset password")
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
            try:
                schema = ResetPasswordSchema(**data)
            except ValidationError as e:
                err     = e.errors()[0]
                message = err['msg'].replace('Value error, ', '')
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            user, error_message = service.reset_password(schema.uid, schema.token, schema.password)
            if user is None:
                return Response(error_response(message=error_message), status=status.HTTP_400_BAD_REQUEST)

            return Response(
                success_response(message="Password reset successfully. Please sign in."),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Reset password error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileApiView(APIView):
    """Read or update the authenticated user's profile.

    GET returns name and contact details.
    PUT updates first/last name, business, and phone.
    """

    def get(self, request):
        """Return the current user's profile payload."""
        try:
            user = request.user
            full_name = f"{user.first_name} {user.last_name}".strip() or user.username or user.email.split("@")[0]
            return Response(success_response(
                message="Profile fetched",
                data={
                    "full_name":     full_name,
                    "first_name":    user.first_name or "",
                    "last_name":     user.last_name or "",
                    "email":         user.email,
                    "business_name": user.business_name or "",
                    "phone":         user.phone or "",
                    "initials":      (full_name[0] if full_name else "U").upper(),
                }
            ), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserProfileApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Update profile fields and return the saved profile."""
        try:
            user         = request.user
            first_name   = request.data.get("first_name", "").strip()
            last_name    = request.data.get("last_name", "").strip()
            business_name = request.data.get("business_name", "").strip()
            phone        = request.data.get("phone", "").strip()

            if not first_name:
                return Response(error_response(message="First name is required."), status=status.HTTP_400_BAD_REQUEST)
            if not last_name:
                return Response(error_response(message="Last name is required."), status=status.HTTP_400_BAD_REQUEST)
            if not business_name:
                return Response(error_response(message="Business name is required."), status=status.HTTP_400_BAD_REQUEST)
            if not phone:
                return Response(error_response(message="Phone number is required."), status=status.HTTP_400_BAD_REQUEST)

            user.first_name    = first_name
            user.last_name     = last_name
            user.business_name = business_name
            user.phone         = phone
            user.save(update_fields=["first_name", "last_name", "business_name", "phone"])

            full_name = f"{user.first_name} {user.last_name}".strip()
            logger.info(f"[PROFILE] Updated for {user.email}")
            return Response(success_response(
                message="Profile updated successfully.",
                data={
                    "full_name":     full_name,
                    "first_name":    user.first_name,
                    "last_name":     user.last_name,
                    "email":         user.email,
                    "business_name": user.business_name or "",
                    "phone":         user.phone or "",
                    "initials":      (full_name[0] if full_name else "U").upper(),
                }
            ), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserProfileApiView PUT error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAccountView(APIView):
    """Permanently delete the authenticated user account.

    Cascades related data owned by the user.
    Requires a valid JWT; no request body needed.
    """

    def delete(self, request):
        """Delete the current user and return a success message."""
        try:
            email = request.user.email
            request.user.delete()
            logger.info(f"[DELETE ACCOUNT] Account deleted: {email}")
            return Response(
                success_response(message="Account deleted successfully."),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"DeleteAccountView error: {e}")
            return Response(error_response(message="Something went wrong."), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
