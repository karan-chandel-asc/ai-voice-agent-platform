from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from pydantic import ValidationError

from .schemas import SignupViewSchema, LoginViewSchema, ForgotPasswordSchema, ResetPasswordSchema
from .service import UserService
from .tasks import send_password_reset_email
from core.logger import logger
from core.response_schemas import success_response, error_response
from django.shortcuts import render
from django.conf import settings


service = UserService()

class SighnUpRender(APIView):
    authentication_classes = []
    permission_classes     = []
    def get(self, request):
        logger.info("Request received for signup Render Html")
        return render(request, 'voice_register.html', {'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID})



class SignupAPIView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        try:

            logger.info("Request received for signup Post Method")
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

            try:
                validated_data = SignupViewSchema(**data)
            except ValidationError as e:
                err = e.errors()[0]
                message = err['msg'].replace('Value error, ', '')
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            email_exists , message = service.check_email_exists(validated_data.work_email)
            if  email_exists is None:
                return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if email_exists:
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            user, err = service.create_user(validated_data)
            if not user:
                return Response(error_response(message=err), status=status.HTTP_400_BAD_REQUEST)

            return Response(success_response(
                message="Signup successful ! you can Login Now"
            ), status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Signup error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginRender(APIView):
    authentication_classes = []
    permission_classes     = []
    def get(self, request):
        logger.info("Request received for login Get Method")
        return render(request, 'voice_login.html', {'GOOGLE_CLIENT_ID': settings.GOOGLE_CLIENT_ID})

class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        try:
            logger.info("Request received for login Post Method")
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

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
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
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
    authentication_classes = []
    permission_classes     = []
    def get(self, request):
        logger.info("Request received for forgot password Render Html")
        return render(request, 'voice_forgot_password.html')

class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
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
    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        logger.info("GET Request received for reset password page")
        return render(request, 'ase_reset_password.html')



class ResetPasswordAPIView(APIView):
    authentication_classes = []
    permission_classes     = []

    def post(self, request):
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


class GoogleRedirectView(APIView):
    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        try:
            from django.shortcuts import redirect
            redirect_uri = settings.GOOGLE_REDIRECT_URI
            auth_url, err = service.get_google_redirect_url(redirect_uri)
            if not auth_url:
                return redirect('/api/auth/login/?error=google_config')
            return redirect(auth_url)
        except Exception as e:
            logger.error(f"Google redirect error: {e}")
            return redirect('/api/auth/login/?error=google_failed')


class GoogleCallbackView(APIView):
    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        try:
            from django.shortcuts import redirect
            code  = request.GET.get('code')
            error = request.GET.get('error')

            if error or not code:
                return redirect('/api/auth/login/?error=google_denied')

            redirect_uri = settings.GOOGLE_REDIRECT_URI
            user, err    = service.exchange_google_code(code, redirect_uri)
            if not user:
                logger.error(f"Google callback error: {err}")
                return redirect('/api/auth/login/?error=google_failed')

            refresh = RefreshToken.for_user(user)
            access  = str(refresh.access_token)
            ref     = str(refresh)
            return redirect(f'/api/dashboard/voice-dashboard/?access={access}&refresh={ref}')
        except Exception as e:
            logger.error(f"Google callback error: {e}")
            return redirect('/api/auth/login/?error=google_failed')


PLAN_LABELS = {
    "free":       "Free",
    "pro":        "Pro — $79/mo",
    "enterprise": "Enterprise — $199/mo",
}

class UserProfileApiView(APIView):
    def get(self, request):
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
                    "plan":          user.plan,
                    "plan_label":    PLAN_LABELS.get(user.plan, user.plan.capitalize()),
                    "initials":      (full_name[0] if full_name else "U").upper(),
                }
            ), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserProfileApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
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
                    "plan":          user.plan,
                    "plan_label":    PLAN_LABELS.get(user.plan, user.plan.capitalize()),
                    "initials":      (full_name[0] if full_name else "U").upper(),
                }
            ), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserProfileApiView PUT error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class DeleteAccountView(APIView):
    def delete(self, request):
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
