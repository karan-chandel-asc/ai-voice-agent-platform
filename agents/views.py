from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from pydantic import ValidationError
from .models import Agent, ElevenLabsVoice
from .serializers import (
    AgentListSerializer, AgentDetailSerializer, ElevenLabsVoiceSerializer,
    UserToolSerializer,
)
from .services import ElevenLabsVoiceMechanism, AgentMechanism, UserToolMechanism
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
