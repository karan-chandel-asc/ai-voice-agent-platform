from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()
LOGIN_URL = '/api/auth/login/'


class JWTCookieAuthentication(BaseAuthentication):
    """Authenticates requests using a JWT stored in the 'access_token' cookie."""

    def authenticate(self, request):
        token_str = request.COOKIES.get('access_token', '')
        if not token_str:
            return None
        try:
            token = AccessToken(token_str)
            user = User.objects.get(pk=token['user_id'])
            return (user, token)
        except (TokenError, InvalidToken, User.DoesNotExist, KeyError, TypeError):
            return None


class RenderAPIView(APIView):
    """Base class for HTML render views. Redirects unauthenticated browsers to login."""

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, (NotAuthenticated, PermissionDenied)):
            path = '/'
            if getattr(self, 'request', None) is not None:
                path = self.request.get_full_path() or '/'
            if path.startswith(LOGIN_URL):
                path = '/api/dashboard/voice-dashboard/'
            return HttpResponseRedirect(f"{LOGIN_URL}?next={quote(path, safe='/')}")
        return super().handle_exception(exc)
