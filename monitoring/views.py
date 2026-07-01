from django.shortcuts import render
from core.auth_utils import RenderAPIView


class VoiceAnalyticsRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_analytics.html')
