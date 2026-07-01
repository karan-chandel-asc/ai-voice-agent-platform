from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, VoiceCampaignsRender, VoiceCampaignCreateRender, VoiceCampaignResultsRender

router = DefaultRouter()
router.register("campaign-api", CampaignViewSet, basename="campaigns")

urlpatterns = [
    path("voice-campaigns/",       VoiceCampaignsRender.as_view(),       name="voice-campaigns"),
    path("voice-campaign-create/", VoiceCampaignCreateRender.as_view(),   name="voice-campaign-create"),
    path("voice-campaign-results/",VoiceCampaignResultsRender.as_view(),  name="voice-campaign-results"),
    path("", include(router.urls)),
]
