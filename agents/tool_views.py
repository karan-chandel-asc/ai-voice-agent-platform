"""HTTP endpoints for Retell custom function / tool calls."""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from pydantic import ValidationError

from core.response_schemas import success_response, error_response
from core.logger import logger
from .schemas import (
    CheckRoomAvailabilitySchema,
    CalculateBookingPriceSchema,
    CreateRoomReservationSchema,
)
from . import tool_services


def _extract_tool_payload(request) -> dict:
    """Normalize Retell custom-function bodies and plain JSON tool args."""
    body = request.data
    if not isinstance(body, dict):
        return {}

    args = body.get("args") if isinstance(body.get("args"), dict) else None
    if args is None and isinstance(body.get("arguments"), dict):
        args = body["arguments"]
    payload = dict(args or body)

    call = body.get("call") if isinstance(body.get("call"), dict) else {}
    if call.get("call_id") and not payload.get("call_id"):
        payload["call_id"] = call.get("call_id")
    if call.get("call_id") and not payload.get("call_sid"):
        payload["call_sid"] = call.get("call_id")

    to_number = (
        call.get("to_number")
        or call.get("agent_number")
        or body.get("to_number")
        or request.query_params.get("to_number")
    )
    if to_number and not payload.get("agent_phone"):
        payload["agent_phone"] = to_number

    agent_id = body.get("agent_id") or request.query_params.get("agent_id")
    if agent_id and not payload.get("agent_id"):
        payload["agent_id"] = agent_id

    # Drop Retell wrapper keys if present at top level
    for key in ("args", "arguments", "call", "name", "tool_call_id"):
        payload.pop(key, None)
    return payload


class _BaseToolApiView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    schema_class = None
    tool_name = "tool"

    def post(self, request):
        try:
            payload = _extract_tool_payload(request)
            logger.info(f"[TOOL] {self.tool_name} payload keys={list(payload.keys())}")
            validated = self.schema_class(**payload)
            result = self.run_tool(validated.model_dump(), payload)
            http = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
            if result.get("success"):
                return Response(
                    success_response(message=result.get("message", ""), data=result.get("data")),
                    status=http,
                )
            return Response(
                error_response(message=result.get("message", "Tool failed"), data=result.get("data")),
                status=http,
            )
        except ValidationError as e:
            msg = "; ".join(
                f"{'.'.join(str(x) for x in err.get('loc', []))}: {err.get('msg')}"
                for err in e.errors()
            )
            return Response(error_response(message=msg), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[TOOL] {self.tool_name} error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def run_tool(self, validated: dict, raw: dict) -> dict:
        raise NotImplementedError


class CheckRoomAvailabilityApiView(_BaseToolApiView):
    schema_class = CheckRoomAvailabilitySchema
    tool_name = "check_room_availability"

    def run_tool(self, validated, raw):
        return tool_services.check_room_availability(
            check_in_date=validated["check_in_date"],
            check_out_date=validated["check_out_date"],
            number_of_guests=validated["number_of_guests"],
            agent_id=raw.get("agent_id"),
            agent_phone=raw.get("agent_phone"),
        )


class CalculateBookingPriceApiView(_BaseToolApiView):
    schema_class = CalculateBookingPriceSchema
    tool_name = "calculate_booking_price"

    def run_tool(self, validated, raw):
        return tool_services.calculate_booking_price(**validated)


class CreateRoomReservationApiView(_BaseToolApiView):
    schema_class = CreateRoomReservationSchema
    tool_name = "create_room_reservation"

    def run_tool(self, validated, raw):
        data = {**validated}
        data["agent_id"] = raw.get("agent_id")
        data["agent_phone"] = raw.get("agent_phone")
        data["call_sid"] = raw.get("call_sid") or raw.get("call_id")
        return tool_services.create_room_reservation(data)
