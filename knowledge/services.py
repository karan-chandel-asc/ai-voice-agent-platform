def semantic_search(agent_id, query, top_k=5):
    """Simple keyword search; replace with FAISS vector search in Week 3."""
    from .models import DocumentChunk
    chunks = DocumentChunk.objects.filter(
        document__agent_id=agent_id,
        document__status="ready",
        content__icontains=query,
    )[:top_k]
    return [{"chunk_id": str(c.id), "content": c.content, "score": 1.0} for c in chunks]
