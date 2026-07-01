from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Campaign, CampaignNumber
from .serializers import CampaignSerializer, CampaignNumberSerializer
from core.auth_utils import RenderAPIView
from .tasks import run_campaign


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return Campaign.objects.filter(agent__owner=self.request.user)

    def perform_create(self, serializer):
        campaign = serializer.save()
        run_campaign.apply_async(args=[str(campaign.id)], eta=campaign.scheduled_at)

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        campaign = self.get_object()
        numbers = campaign.numbers.all()
        return Response(CampaignNumberSerializer(numbers, many=True).data)


class VoiceCampaignsRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_campaigns.html')


class VoiceCampaignCreateRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_campaign_create.html')


class VoiceCampaignResultsRender(RenderAPIView):
    def get(self, request):
        pk = request.GET.get('pk', '')
        return render(request, 'voice_campaign_results.html', {'pk': pk})
