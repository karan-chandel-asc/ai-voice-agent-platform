from django.urls import path
from .views import (
    ElevenlabsVoiceListView,
    AgentListApiView,
    AgentCRUDApiView,
    DeleteAllAgentsView,
    VoiceAgentsRender,
    VoiceCreateAgentRender,
    VoiceAgentDetailRender,
    ManageToolsRender,
    UserToolListApiView,
    UserToolDetailApiView,
)

urlpatterns = [
    path("voice-agents/", VoiceAgentsRender.as_view(), name="voice-agents"),
    path("voice-create-agent/", VoiceCreateAgentRender.as_view(), name="voice-create-agent"),
    path("voice-agent-detail/", VoiceAgentDetailRender.as_view(), name="voice-agent-detail"),
    path("voices-list-api/", ElevenlabsVoiceListView.as_view(), name="elevenlabs-voices"),
    path("create-agent-api/", AgentCRUDApiView.as_view(), name="agent-create"),
    path("agent-list-api/", AgentListApiView.as_view(), name="agent-list"),
    path("get-agent-detail/<str:pk>/", AgentCRUDApiView.as_view(), name="agent-crud"),
    path("delete-agent/<str:pk>/", AgentCRUDApiView.as_view(), name="agent-delete"),
    path("update-agent/<str:pk>/", AgentCRUDApiView.as_view(), name="agent-update"),
    path("delete-all-agents/", DeleteAllAgentsView.as_view(), name="delete-all-agents"),
    path("user-tools/", UserToolListApiView.as_view(), name="user-tool-list"),
    path("user-tools/<str:pk>/", UserToolDetailApiView.as_view(), name="user-tool-detail"),
    path("manage-tools/", ManageToolsRender.as_view(), name="manage-tools"),
]
