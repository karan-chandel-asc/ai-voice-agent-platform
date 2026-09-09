from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from pydantic import ValidationError
from .models import Agent, ElevenLabsVoices
from .serializers import (
    AgentListSerializer, AgentDetailSerializer, ElevenLabsVoicesSerializer,
    RetellLanguageSerializer, RetellPhoneNumberSerializer,
)
from .services import (
    ElevenLabsVoicesMechanism, AgentMechanism,
    RetellLanguageMechanism, RetellPhoneMechanism,
)
from .retell_services import retell_services
from .schemas import CreateAgentSchema, UpdateAgentSchema
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


class ElevenlabsVoiceListView(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            logger.info("Request received for ElevenlabsVoiceView")
            voice_class = ElevenLabsVoicesMechanism()

            voices, message = voice_class.get_all_ElevenLabs_voices()
            if voices is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            paginator  = self.pagination_class()
            paginated  = paginator.paginate_queryset(voices, request)
            serializer = ElevenLabsVoicesSerializer(paginated, many=True)
            return paginator.get_paginated_response(
                success_response(message=message, data=serializer.data)
            )
        except Exception as e:
            logger.error(f"ElevenlabsVoiceView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncRetellVoicesApiView(APIView):
    """Pull all voices from Retell and save into ElevenLabsVoices."""

    def post(self, request):
        try:
            logger.info("Request received for SyncRetellVoicesApiView")
            data, message = retell_services.sync_voices_to_db()
            if data is None:
                return Response(error_response(message=message), status=status.HTTP_502_BAD_GATEWAY)
            return Response(
                success_response(message=message, data=data),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"SyncRetellVoicesApiView error: {e}")
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
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

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
            data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

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


class SyncRetellLanguagesApiView(APIView):
    """Upsert Retell language catalog into RetellLanguage."""

    def post(self, request):
        try:
            logger.info("Request received for SyncRetellLanguagesApiView")
            data, message = retell_services.sync_languages_to_db()
            if data is None:
                return Response(error_response(message=message), status=status.HTTP_502_BAD_GATEWAY)
            return Response(success_response(message=message, data=data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"SyncRetellLanguagesApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetellLanguageListApiView(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            search = request.query_params.get("search", "").strip()
            langs, message = RetellLanguageMechanism().get_all(search=search or None)
            if langs is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            paginator = self.pagination_class()
            paginated = paginator.paginate_queryset(langs, request)
            serializer = RetellLanguageSerializer(paginated, many=True)
            return paginator.get_paginated_response(success_response(message=message, data=serializer.data))
        except Exception as e:
            logger.error(f"RetellLanguageListApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncRetellPhonesApiView(APIView):
    """Sync Retell phone numbers + seed Twilio env numbers."""

    def post(self, request):
        try:
            logger.info("Request received for SyncRetellPhonesApiView")
            data, message = retell_services.sync_phone_numbers_to_db()
            if data is None:
                return Response(error_response(message=message), status=status.HTTP_502_BAD_GATEWAY)
            return Response(success_response(message=message, data=data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"SyncRetellPhonesApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncRetellAgentsApiView(APIView):
    """Upsert Retell agents locally; delete Deskline agents removed on Retell (never deletes on Retell)."""

    def post(self, request):
        try:
            logger.info("Request received for SyncRetellAgentsApiView")
            data, message = AgentMechanism().sync_agents_with_retell(request.user)
            if data is None:
                return Response(error_response(message=message), status=status.HTTP_502_BAD_GATEWAY)
            return Response(success_response(message=message, data=data), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"SyncRetellAgentsApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateWebCallApiView(APIView):
    """Create a Retell web call access token for in-browser agent testing."""

    def post(self, request, pk):
        try:
            logger.info(f"Request received for CreateWebCallApiView pk={pk}")
            agent, message = AgentMechanism().get_agent_by_id(pk, request.user)
            if agent is None:
                return Response(error_response(message=message), status=status.HTTP_404_NOT_FOUND)

            if not agent.retell_agent_id:
                return Response(
                    error_response(message="Agent is not synced to Retell. Sync or create it on Retell first."),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data, msg = retell_services.create_web_call(
                retell_agent_id=agent.retell_agent_id,
                metadata={
                    "deskline_agent_id": str(agent.id),
                    "deskline_user_id": str(request.user.id),
                    "source": "deskline_test",
                },
            )
            if data is None:
                return Response(error_response(message=msg), status=status.HTTP_502_BAD_GATEWAY)

            if not data.get("access_token"):
                return Response(
                    error_response(message="Retell did not return an access token"),
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            return Response(
                success_response(
                    message=msg,
                    data={
                        **data,
                        "agent_name": agent.agent_name,
                        "deskline_agent_id": str(agent.id),
                    },
                ),
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"CreateWebCallApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetellPhoneListApiView(APIView):
    pagination_class = Pagination

    def get(self, request):
        try:
            search = request.query_params.get("search", "").strip()
            available = request.query_params.get("available", "").lower() in ("1", "true", "yes")
            phones, message = RetellPhoneMechanism().get_all(
                available_only=available,
                search=search or None,
            )
            if phones is None:
                return Response(error_response(message=message), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            paginator = self.pagination_class()
            paginated = paginator.paginate_queryset(phones, request)
            serializer = RetellPhoneNumberSerializer(paginated, many=True)
            return paginator.get_paginated_response(success_response(message=message, data=serializer.data))
        except Exception as e:
            logger.error(f"RetellPhoneListApiView error: {e}")
            return Response(error_response(message="Something went wrong"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
