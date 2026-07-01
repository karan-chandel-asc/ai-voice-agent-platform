from django.urls import path
from .views import VoiceAnalyticsRender

urlpatterns = [
    path("voice-analytics/", VoiceAnalyticsRender.as_view(), name="voice-analytics"),
]
