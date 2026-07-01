from django.urls import path
from .views import (
    SighnUpRender, SignupAPIView,
    LoginRender, LoginAPIView,
    LogoutView,
    GoogleRedirectView, GoogleCallbackView,
    ForgotPasswordRender, ForgotPasswordView,
    ResetPasswordRender, ResetPasswordAPIView,
    UserProfileApiView,
    DeleteAccountView,
)

urlpatterns = [
    path('signup/',                 SighnUpRender.as_view(),        name='signup-render'),
    path('signup/api/',             SignupAPIView.as_view(),         name='signup-api'),
    path('login/',                  LoginRender.as_view(),           name='login-render'),
    path('login/api/',              LoginAPIView.as_view(),          name='login-api'),
    path('logout/',                 LogoutView.as_view(),            name='logout'),
    path('google/redirect/',        GoogleRedirectView.as_view(),    name='google-redirect'),
    path('google/callback/',        GoogleCallbackView.as_view(),    name='google-callback'),
    path('forgot-password/',        ForgotPasswordRender.as_view(),  name='forgot-password-render'),
    path('forgot-password/api/',    ForgotPasswordView.as_view(),    name='forgot-password-api'),
    path('reset-password/',         ResetPasswordRender.as_view(),   name='reset-password-render'),
    path('reset-password/api/',     ResetPasswordAPIView.as_view(),  name='reset-password-api'),
    path('profile/',                UserProfileApiView.as_view(),    name='user-profile'),
    path('delete-account/',         DeleteAccountView.as_view(),     name='delete-account'),
]
