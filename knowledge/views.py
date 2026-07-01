import os
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.auth_utils import RenderAPIView
from core.response_schemas import success_response, error_response
from core.logger import logger

from agents.models import Agent
from .models import AgentDocument
from .serializers import AgentDocumentSerializer
from .tasks import index_document_task


class VoiceKnowledgeBaseRender(RenderAPIView):
    def get(self, request):
        return render(request, 'voice_knowledge_base.html')


class AgentListForKBView(APIView):
    def get(self, request):
        agents = Agent.objects.filter(owner=request.user).values('id', 'agent_name', 'status')
        return Response(success_response(
            message="Agents fetched",
            data=list(agents),
        ))


class DocumentListView(APIView):
    def get(self, request):
        agent_id = request.query_params.get('agent_id')

        if agent_id:
            try:
                agent = Agent.objects.get(id=agent_id, owner=request.user)
            except Agent.DoesNotExist:
                return Response(error_response(message="Agent not found"), status=404)
            docs_qs = AgentDocument.objects.filter(agent=agent).select_related('agent')
        else:
            docs_qs = AgentDocument.objects.filter(agent__owner=request.user).select_related('agent')

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        page_size = 5
        total        = docs_qs.count()
        total_chunks = sum(docs_qs.values_list('chunk_count', flat=True))
        total_pages  = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        docs   = docs_qs[offset:offset + page_size]

        serializer = AgentDocumentSerializer(docs, many=True, context={'request': request})

        last_doc     = docs_qs.order_by('-updated_at').first()
        last_updated = last_doc.updated_at.isoformat() if last_doc else None

        return Response(success_response(
            message="Documents fetched",
            data={
                "documents":   serializer.data,
                "total_docs":  total,
                "total_chunks": total_chunks,
                "last_updated": last_updated,
                "pagination": {
                    "page":       page,
                    "page_size":  page_size,
                    "total":      total,
                    "total_pages": total_pages,
                },
            },
        ))


class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        agent_id = request.data.get('agent_id')
        file = request.FILES.get('file')

        if not agent_id:
            return Response(error_response(message="agent_id is required"), status=400)
        if not file:
            return Response(error_response(message="file is required"), status=400)

        allowed_ext = {'.pdf', '.docx', '.doc', '.txt', '.md'}
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in allowed_ext:
            return Response(
                error_response(message="Unsupported file type. Allowed: PDF, DOCX, DOC, TXT, MD"),
                status=400,
            )

        if file.size > 10 * 1024 * 1024:
            return Response(error_response(message="File size must be under 10MB"), status=400)

        try:
            agent = Agent.objects.get(id=agent_id, owner=request.user)
        except Agent.DoesNotExist:
            return Response(error_response(message="Agent not found"), status=404)

        doc = AgentDocument.objects.create(
            agent=agent,
            title=file.name,
            file=file,
            status="pending",
        )

        index_document_task.delay(str(doc.id))
        logger.info(f"[KB] Upload queued: '{doc.title}' → agent '{agent.agent_name}'")

        return Response(success_response(
            message="Document uploaded. Indexing started.",
            data=AgentDocumentSerializer(doc, context={'request': request}).data,
        ), status=201)


class DocumentDeleteView(APIView):
    def delete(self, request, doc_id):
        try:
            doc = AgentDocument.objects.get(id=doc_id, agent__owner=request.user)
        except AgentDocument.DoesNotExist:
            return Response(error_response(message="Document not found"), status=404)

        try:
            from .pipnecone import PineconeService
            PineconeService().delete_document(str(doc.id))
        except Exception as e:
            logger.warning(f"[KB] Pinecone delete warning for {doc_id}: {e}")

        title = doc.title
        doc.delete()
        logger.info(f"[KB] Deleted document: '{title}'")
        return Response(success_response(message="Document deleted successfully"))
