import string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from pydantic import ValidationError
from .models import Agent, ElevenLabsVoice, Booking
from .serializers import (
    AgentListSerializer, AgentDetailSerializer, ElevenLabsVoiceSerializer,
    PhoneNumberSerializer, UserToolSerializer,
)
from .services import ElevenLabsVoiceMechanism, AgentMechanism, PhoneNumberMechanism, UserToolMechanism
from .schemas import CreateAgentSchema, UpdateAgentSchema, CreateUserToolSchema, UpdateUserToolSchema
from core.response_schemas import success_response, error_response
from core.pagination import Pagination
from core.logger import logger
from core.auth_utils import RenderAPIView
from django.shortcuts import render


class VoiceAgentsRender(RenderAPIView):
    def get(self, request):
        logger.info("Request received for voice agents Render Html")
        return render(request, 'voice_agents.html')


class VoiceCreateAgentRender(RenderAPIView):
    def get(self, request):
        logger.info("Request received for voice create agent Render Html")
        return render(request, 'voice_agent_create.html')


class VoiceAgentDetailRender(RenderAPIView):
    def get(self, request):
        logger.info("Request received for voice agent detail Render Html")
        pk = request.GET.get('pk', '')
        return render(request, 'voice_agent_detail.html', {'pk': pk})


class ManageToolsRender(RenderAPIView):
    def get(self, request):
        logger.info("Request received for ManageToolsRender Html")
        return render(request, 'voice_manage_tools.html')


class ElevenlabsVoiceListView(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            logger.info("Request received for ElevenlabsVoiceView")
            voice_class = ElevenLabsVoiceMechanism()

            voices, message = voice_class.get_all_ElevenLabs_voices()
            if voices is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            paginator  = self.pagination_class()
            paginated  = paginator.paginate_queryset(voices, request)
            serializer = ElevenLabsVoiceSerializer(paginated, many=True)
            return paginator.get_paginated_response(
                success_response(message=message, data=serializer.data)
            )
        except Exception as e:
            logger.error(f"ElevenlabsVoiceView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PhoneNumberCatalogListApiForCreateAgent(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            logger.info("Request received for PhoneNumberCatalogListApiForCreateAgent")
            agent_service = PhoneNumberMechanism()
            agents, message = agent_service.get_available_numbers()
            if agents is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            paginator  = self.pagination_class()
            paginated  = paginator.paginate_queryset(agents, request)
            serializer = PhoneNumberSerializer(paginated, many=True)
            return paginator.get_paginated_response(
                success_response(message=message, data=serializer.data)
            )
        except Exception as e:
            logger.error(f"PhoneNumberCatalogListApiForCreateAgent error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
class AgentListApiView(APIView):
    pagination_class = Pagination
    def get(self, request):
        try:
            logger.info("Request received for AgentListApiView")
            agent_service = AgentMechanism()
            search = request.query_params.get('search', '').strip()
            agents, message = agent_service.get_all_agents(request.user, search=search or None)
            if agents is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            paginator  = self.pagination_class()
            paginated  = paginator.paginate_queryset(agents, request)
            serializer = AgentListSerializer(paginated, many=True)
            return paginator.get_paginated_response(
                success_response(message=message, data=serializer.data)
            )
        except Exception as e:
            logger.error(f"AgentListApiView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AgentCRUDApiView(APIView):

    def get(self, request, pk):
        try:
            logger.info(f"Request received for AgentCRUDApiView GET pk={pk}")
            agent_service = AgentMechanism()
            agent, message = agent_service.get_agent_by_id(pk, request.user)
            if agent is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)
            serializer = AgentDetailSerializer(agent)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"AgentCRUDApiView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            logger.info("Request received for AgentCRUDApiView POST")
            import json as _json
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

            if 'user_tools' in data and isinstance(data['user_tools'], str):
                try:
                    data['user_tools'] = _json.loads(data['user_tools'])
                except Exception:
                    data['user_tools'] = []

            try:
                validated_data = CreateAgentSchema(**data)
            except ValidationError as e:
                err = e.errors()[0]
                message = err['msg'].replace('Value error, ', '')
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            agent_service = AgentMechanism()
            agent, message = agent_service.create_agent(request.user, validated_data)
            if agent is None:
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            serializer = AgentDetailSerializer(agent)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"AgentCRUDApiView POST error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def delete(self, request, pk):
        try:
            logger.info(f"Request received for AgentCRUDApiView DELETE pk={pk}")
            agent_service = AgentMechanism()
            agent, message = agent_service.delete_agent(pk, request.user)
            if agent is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)
            return Response(success_response(message=message), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"AgentCRUDApiView DELETE error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    def put(self, request, pk):
        try:
            logger.info(f"Request received for AgentCRUDApiView PUT pk={pk}")
            import json as _json
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

            if 'user_tools' in data and isinstance(data['user_tools'], str):
                try:
                    data['user_tools'] = _json.loads(data['user_tools'])
                except Exception:
                    data['user_tools'] = None

            try:
                validated_data = UpdateAgentSchema(**data)
            except ValidationError as e:
                err = e.errors()[0]
                message = err['msg'].replace('Value error, ', '')
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            agent_service = AgentMechanism()
            agent, message = agent_service.update_agent(pk, request.user, validated_data)
            if agent is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)
            serializer = AgentDetailSerializer(agent)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"AgentCRUDApiView PUT error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAllAgentsView(APIView):
    def delete(self, request):
        try:
            queryset = Agent.objects.filter(owner=request.user)
            agent_count = queryset.count()
            queryset.delete()
            logger.info(f"[DELETE ALL AGENTS] {agent_count} agents deleted for {request.user}")
            return Response(
                success_response(
                    message=f"{agent_count} agent(s) deleted successfully.",
                    data={"deleted": agent_count}
                ),
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception(f"DeleteAllAgentsView error: {e}")
            return Response(
                error_response(message="Something went wrong."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class UserToolListApiView(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            logger.info("Request received for UserToolListApiView GET")
            search = request.query_params.get("search", "").strip()
            service = UserToolMechanism()
            tools, message = service.get_all_user_tools(request.user, search=search or None)
            if tools is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            paginator  = self.pagination_class()
            paginated  = paginator.paginate_queryset(tools, request)
            serializer = UserToolSerializer(paginated, many=True)
            return paginator.get_paginated_response(
                success_response(message=message, data=serializer.data)
            )
        except Exception as e:
            logger.error(f"UserToolListApiView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            logger.info("Request received for UserToolListApiView POST")
            import json as _json
            data = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)

            if "parameters" in data and isinstance(data["parameters"], str):
                try:
                    data["parameters"] = _json.loads(data["parameters"])
                except Exception:
                    data["parameters"] = {}

            try:
                validated = CreateUserToolSchema(**data)
            except ValidationError as e:
                err = e.errors()[0]
                message = err["msg"].replace("Value error, ", "")
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            service = UserToolMechanism()
            tool, message = service.create_tool(request.user, validated)
            if tool is None:
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            serializer = UserToolSerializer(tool)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"UserToolListApiView POST error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserToolDetailApiView(APIView):

    def get(self, request, pk):
        try:
            logger.info(f"Request received for UserToolDetailApiView GET pk={pk}")
            service = UserToolMechanism()
            tool, message = service.get_tool_by_id(pk, request.user)
            if tool is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)

            serializer = UserToolSerializer(tool)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserToolDetailApiView GET error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            logger.info(f"Request received for UserToolDetailApiView PUT pk={pk}")
            import json as _json
            data = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)

            if "parameters" in data and isinstance(data["parameters"], str):
                try:
                    data["parameters"] = _json.loads(data["parameters"])
                except Exception:
                    data["parameters"] = None

            try:
                validated = UpdateUserToolSchema(**data)
            except ValidationError as e:
                err = e.errors()[0]
                message = err["msg"].replace("Value error, ", "")
                return Response(error_response(message=message), status=status.HTTP_400_BAD_REQUEST)

            service = UserToolMechanism()
            tool, message = service.update_tool(pk, request.user, validated)
            if tool is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)

            serializer = UserToolSerializer(tool)
            return Response(success_response(message=message, data=serializer.data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserToolDetailApiView PUT error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            logger.info(f"Request received for UserToolDetailApiView DELETE pk={pk}")
            service = UserToolMechanism()
            result, message = service.delete_tool(pk, request.user)
            if result is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)

            return Response(success_response(message=message), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserToolDetailApiView DELETE error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _int(val, default=1) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _resolve_agent(agent_id: str | None):
    if not agent_id:
        return None
    try:
        return Agent.objects.get(id=agent_id)
    except Agent.DoesNotExist:
        return None


def _mark_call_booked(call_sid: str):
    if call_sid:
        from calls.models import CallLog
        CallLog.objects.filter(twilio_call_sid=call_sid).update(outcome="booked")


class BookTableWebhookView(APIView):
    """
    Webhook called by the voice engine when the LLM triggers book_table tool.
    No JWT auth — called server-to-server from FastAPI.
    Expects JSON: { guest_name, date, time, guests, phone?, guest_email?,
                    meal_preference?, special_requests?, agent_id?, call_sid? }
    Returns JSON the LLM reads back to the caller.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import string
        from datetime import datetime

        data = request.data

        required = ["guest_name", "date", "time", "guests"]
        missing  = [f for f in required if not data.get(f)]
        if missing:
            return Response(
                {"success": False, "message": f"Missing fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from datetime import date as date_cls, timedelta
            raw_date = data["date"].strip().lower()
            if raw_date == "today":
                date_obj = date_cls.today()
            elif raw_date in ("tomorrow", "tommorrow"):
                date_obj = date_cls.today() + timedelta(days=1)
            else:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        date_obj = datetime.strptime(raw_date, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("no format matched")
            raw_time = data["time"].strip()
            for tfmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
                try:
                    time_obj = datetime.strptime(raw_time, tfmt).time()
                    break
                except ValueError:
                    continue
            else:
                raise ValueError("no time format matched")
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid date or time format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        call_sid = data.get("call_sid", "")

        booking = Booking.objects.create(
            agent            = _resolve_agent(data.get("agent_id")),
            call_sid         = call_sid,
            booking_type     = "table",
            guest_name       = data["guest_name"],
            guest_email      = data.get("guest_email", ""),
            phone            = data.get("phone", ""),
            date             = date_obj,
            time             = time_obj,
            guests           = _int(data.get("guests")),
            meal_preference  = data.get("meal_preference", ""),
            special_requests = data.get("special_requests", ""),
        )

        _mark_call_booked(call_sid)
        logger.info(f"[BOOKING:TABLE] {booking.guest_name} — {booking.date} {booking.time}")

        return Response({
            "success": True,
            "message": (
                f"Table booked for {booking.guest_name}, party of {booking.guests} "
                f"on {date_obj.strftime('%A, %B %d')} at {time_obj.strftime('%I:%M %p')}. "
                f"We will send a confirmation email once approved."
            ),
        })


class BookRoomWebhookView(APIView):
    """
    Webhook called by the voice engine when the LLM triggers book_room tool.
    No JWT auth — called server-to-server from FastAPI.
    Expects JSON: { guest_name, email, check_in_date, check_out_date, room_type,
                    guests?, phone?, special_requests?, agent_id?, call_sid? }
    Returns JSON the LLM reads back to the caller.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from datetime import datetime

        data = request.data

        required = ["guest_name", "email", "check_in_date", "check_out_date", "room_type"]
        missing  = [f for f in required if not data.get(f)]
        if missing:
            return Response(
                {"success": False, "message": f"Missing fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            check_in_obj  = datetime.strptime(data["check_in_date"],  "%Y-%m-%d").date()
            check_out_obj = datetime.strptime(data["check_out_date"], "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if check_out_obj <= check_in_obj:
            return Response(
                {"success": False, "message": "Check-out must be after check-in."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nights   = (check_out_obj - check_in_obj).days
        call_sid = data.get("call_sid", "")

        booking = Booking.objects.create(
            agent            = _resolve_agent(data.get("agent_id")),
            call_sid         = call_sid,
            booking_type     = "room",
            guest_name       = data["guest_name"],
            guest_email      = data.get("email", ""),
            phone            = data.get("phone", ""),
            date             = check_in_obj,
            time             = datetime.strptime("14:00", "%H:%M").time(),
            guests           = _int(data.get("guests", 1), 1),
            room_type        = data["room_type"],
            check_in         = check_in_obj,
            check_out        = check_out_obj,
            nights           = nights,
            special_requests = data.get("special_requests", ""),
        )

        _mark_call_booked(call_sid)
        logger.info(f"[BOOKING:ROOM] {booking.guest_name} — {booking.room_type} — {check_in_obj} to {check_out_obj} ({nights}n)")

        return Response({
            "success": True,
            "message": (
                f"Room booked for {booking.guest_name}. {booking.room_type.capitalize()} room, "
                f"check-in {check_in_obj.strftime('%B %d')}, check-out {check_out_obj.strftime('%B %d')}, "
                f"{nights} night{'s' if nights != 1 else ''}. "
                f"We will send a confirmation email once approved."
            ),
        })
