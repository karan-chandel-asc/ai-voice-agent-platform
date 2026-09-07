from django.urls import path
from .views import (
    LoginRender, LoginAPIView,
    LogoutView,
    ForgotPasswordRender, ForgotPasswordView,
    ResetPasswordRender, ResetPasswordAPIView,
    UserProfileApiView,
    DeleteAccountView,
)

urlpatterns = [
    path('login/',                  LoginRender.as_view(),           name='login-render'),
    path('login/api/',              LoginAPIView.as_view(),          name='login-api'),
    path('logout/',                 LogoutView.as_view(),            name='logout'),
    path('forgot-password/',        ForgotPasswordRender.as_view(),  name='forgot-password-render'),
    path('forgot-password/api/',    ForgotPasswordView.as_view(),    name='forgot-password-api'),
    path('reset-password/',         ResetPasswordRender.as_view(),   name='reset-password-render'),
    path('reset-password/api/',     ResetPasswordAPIView.as_view(),  name='reset-password-api'),
    path('profile/',                UserProfileApiView.as_view(),    name='user-profile'),
    path('delete-account/',         DeleteAccountView.as_view(),     name='delete-account'),
]
