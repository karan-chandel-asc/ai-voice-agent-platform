from django.urls import path
from .views import VoiceIntegrationsRender, IntegrationListView, IntegrationToggleView

urlpatterns = [
    path("voice-integrations/",  VoiceIntegrationsRender.as_view(), name="voice-integrations"),
    path("integrations-status/", IntegrationListView.as_view(),     name="integration-status"),
    path("integrations-toggle/", IntegrationToggleView.as_view(),   name="integration-toggle"),
]
