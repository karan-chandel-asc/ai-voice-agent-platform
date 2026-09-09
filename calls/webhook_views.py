"""Single Retell webhook endpoint for call lifecycle events."""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.logger import logger
from core.response_schemas import success_response, error_response
from .webhook_services import process_retell_webhook

LOG = "[RETELL WEBHOOK]"


class RetellCallWebhookView(APIView):
    """
    POST /api/calls/retell-webhook/

    Retell events:
      - call_started  → store CallLog with call_id only
      - call_ended    → update same row (duration, recording, transcript, status)
      - call_analyzed → save call.call_analysis onto CallLog (sentiment + summary)
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            payload = request.data if isinstance(request.data, dict) else {}
            event = payload.get("event")
            call = payload.get("call") if isinstance(payload.get("call"), dict) else {}
            call_id = call.get("call_id") if call else None

            logger.info(
                f"{LOG} HTTP POST received event={event} call_id={call_id} "
                f"keys={list(payload.keys())}"
            )
            result = process_retell_webhook(payload)

            if not result.get("ok"):
                logger.warning(
                    f"{LOG} HTTP 400 event={event} call_id={call_id} "
                    f"reason={result.get('message')}"
                )
                return Response(
                    error_response(message=result.get("message", "Webhook failed")),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(
                f"{LOG} HTTP 200 event={event} call_id={call_id} "
                f"message={result.get('message')}"
            )
            return Response(
                success_response(message=result.get("message", "OK"), data=result),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception(f"{LOG} HTTP 500 unexpected error: {e}")
            return Response(
                error_response(message="Something went wrong"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
