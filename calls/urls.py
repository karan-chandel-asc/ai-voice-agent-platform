from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CallLogDetailView,
    CallLogListView,
    CallLogBulkDeleteView,
    DropDownsoptionsForCallHistory,
    VoiceCallHistoryRender,
    VoiceCallDetailRender,
    DemoTokenView,
    AgentCallStatsView,
    AnalyticsView,
)
from .webhook_views import RetellCallWebhookView

urlpatterns = [
    path("retell-webhook/", RetellCallWebhookView.as_view(), name="retell-call-webhook"),
    path("voice-call-history/", VoiceCallHistoryRender.as_view(),  name="voice-call-history"),
    path("voice-call-detail/",  VoiceCallDetailRender.as_view(),   name="voice-call-detail"),
    path("call-history/dropdowns/", DropDownsoptionsForCallHistory.as_view(), name="call-history-dropdowns"),
    path("call-history/", CallLogListView.as_view(), name="call-history-list"),
    path("call-history/bulk-delete/", CallLogBulkDeleteView.as_view(), name="call-history-bulk-delete"),
    path("call-history/<uuid:pk>/", CallLogDetailView.as_view(), name="call-history-detail"),
    path("demo-token/",             DemoTokenView.as_view(),     name="demo-token"),
    path("agent-stats/<str:agent_id>/", AgentCallStatsView.as_view(), name="agent-call-stats"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]
