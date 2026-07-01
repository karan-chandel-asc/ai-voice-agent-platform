import os
from celery import shared_task
from core.logger import logger


@shared_task
def index_document_task(doc_id: str):
    """Load file → chunk → embed → upsert to Pinecone. Updates AgentDocument status."""
    from .models import AgentDocument
    from .pipnecone import PineconeService
    from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    try:
        doc = AgentDocument.objects.get(id=doc_id)
        doc.status = "processing"
        doc.save(update_fields=["status"])

        file_path = doc.file.path
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext in (".docx", ".doc"):
            loader = Docx2txtLoader(file_path)
        elif ext in (".txt", ".md"):
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            raise RuntimeError(f"Unsupported file type: {ext}")

        loaded_docs = loader.load()
        if not loaded_docs:
            raise RuntimeError("No content extracted from document")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = splitter.split_documents(loaded_docs)

        # PyPDFLoader sets page as 0-indexed; +1 for human-readable page numbers
        chunks_meta = [
            {
                "text": s.page_content,
                "page": (s.metadata.get("page") or 0) + 1,
            }
            for s in splits
            if s.page_content.strip()
        ]

        if not chunks_meta:
            raise RuntimeError("No text content found in document")

        pc = PineconeService()
        count = pc.index_document(str(doc.id), doc.title, chunks_meta)

        doc.status = "ready"
        doc.chunk_count = count
        doc.save(update_fields=["status", "chunk_count"])
        logger.info(f"[KB] Indexed '{doc.title}' — {count} chunks (agent: {doc.agent.agent_name})")

    except AgentDocument.DoesNotExist:
        logger.error(f"[KB] Document {doc_id} not found")
    except Exception as e:
        logger.error(f"[KB] Indexing failed for {doc_id}: {e}", exc_info=True)
        AgentDocument.objects.filter(id=doc_id).update(status="error")
