from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from core.auth_utils import RenderAPIView
from core.logger import logger
from .models import Integration
from .serializers import IntegrationSerializer
from core.response_schemas import success_response, error_response


class VoiceIntegrationsRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_integrations.html')


class IntegrationListView(APIView):
    def get(self, request):
        try:
            logger.info(f"[INTEGRATIONS] List requested by {request.user}")
            objs = []
            for int_type, _ in Integration.TYPE_CHOICES:
                obj, _ = Integration.objects.get_or_create(user=request.user, type=int_type)
                objs.append(obj)
            serializer = IntegrationSerializer(objs, many=True)
            return Response(success_response(message="Integrations fetched successfully", data=serializer.data), status=200)
        except Exception as e:
            logger.error(f"IntegrationListView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IntegrationToggleView(APIView):
    def post(self, request):
        try:
            int_type = request.data.get("type")
            connect  = request.data.get("connect")

            valid_types = [t for t, _ in Integration.TYPE_CHOICES]
            if int_type not in valid_types:
                return Response(error_response(message="Invalid integration type."), status=status.HTTP_400_BAD_REQUEST)

            obj, _ = Integration.objects.get_or_create(user=request.user, type=int_type)
            obj.is_connected = bool(connect)
            obj.connected_at = timezone.now() if connect else None
            obj.save()

            if connect and int_type == 'google_sheets':
                from .tasks import send_daily_call_report
                send_daily_call_report.delay()

            logger.info(f"[INTEGRATIONS] {int_type} {'connected' if connect else 'disconnected'} by {request.user}")
            return Response(success_response(message=f"Integration {'connected' if connect else 'disconnected'} successfully.", data=IntegrationSerializer(obj).data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"IntegrationToggleView POST error: {e}")
            return Response(error_response(message="Something went wrong."), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


