from django.urls import path
from .views import (
    ElevenlabsVoiceListView,
    SyncRetellVoicesApiView,
    SyncRetellLanguagesApiView,
    RetellLanguageListApiView,
    SyncRetellPhonesApiView,
    SyncRetellAgentsApiView,
    CreateWebCallApiView,
    RetellPhoneListApiView,
    AgentListApiView,
    AgentCRUDApiView,
    DeleteAllAgentsView,
    VoiceAgentsRender,
    VoiceCreateAgentRender,
    VoiceAgentDetailRender,
)
from .tool_views import (
    CheckRoomAvailabilityApiView,
    CalculateBookingPriceApiView,
    CreateRoomReservationApiView,
    CheckTableAvailabilityApiView,
    CreateTableReservationApiView,
)

urlpatterns = [
    # Retell custom-function / tool webhooks
    path("tools/check-room-availability/", CheckRoomAvailabilityApiView.as_view(), name="tool-check-room-availability"),
    path("tools/calculate-booking-price/", CalculateBookingPriceApiView.as_view(), name="tool-calculate-booking-price"),
    path("tools/create-room-reservation/", CreateRoomReservationApiView.as_view(), name="tool-create-room-reservation"),
    path("tools/check-table-availability/", CheckTableAvailabilityApiView.as_view(), name="tool-check-table-availability"),
    path("tools/create-table-reservation/", CreateTableReservationApiView.as_view(), name="tool-create-table-reservation"),

    path("voice-agents/", VoiceAgentsRender.as_view(), name="voice-agents"),
    path("voice-create-agent/", VoiceCreateAgentRender.as_view(), name="voice-create-agent"),
    path("voice-agent-detail/", VoiceAgentDetailRender.as_view(), name="voice-agent-detail"),
    path("voices-list-api/", ElevenlabsVoiceListView.as_view(), name="elevenlabs-voices"),
    path("sync-retell-voices/", SyncRetellVoicesApiView.as_view(), name="sync-retell-voices"),
    path("languages-list-api/", RetellLanguageListApiView.as_view(), name="retell-languages"),
    path("sync-retell-languages/", SyncRetellLanguagesApiView.as_view(), name="sync-retell-languages"),
    path("phones-list-api/", RetellPhoneListApiView.as_view(), name="retell-phones"),
    path("sync-retell-phones/", SyncRetellPhonesApiView.as_view(), name="sync-retell-phones"),
    path("sync-retell-agents/", SyncRetellAgentsApiView.as_view(), name="sync-retell-agents"),
    path("create-web-call/<str:pk>/", CreateWebCallApiView.as_view(), name="agent-create-web-call"),
    path("create-agent-api/", AgentCRUDApiView.as_view(), name="agent-create"),
    path("agent-list-api/", AgentListApiView.as_view(), name="agent-list"),
    path("get-agent-detail/<str:pk>/", AgentCRUDApiView.as_view(), name="agent-crud"),
    path("delete-agent/<str:pk>/", AgentCRUDApiView.as_view(), name="agent-delete"),
    path("update-agent/<str:pk>/", AgentCRUDApiView.as_view(), name="agent-update"),
    path("delete-all-agents/", DeleteAllAgentsView.as_view(), name="delete-all-agents"),
]
