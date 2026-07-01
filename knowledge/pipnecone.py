import os
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from core.logger import logger

# Loaded once at worker startup — shared across all tasks in this process
logger.info("[KB] Loading embedding model BAAI/bge-large-en-v1.5 ...")
_EMBED_MODEL = SentenceTransformer("BAAI/bge-large-en-v1.5")
logger.info("[KB] Embedding model ready.")

# Pinecone index — cached per worker process
_INDEX_CACHE = None


def _get_index():
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE

    pc         = Pinecone(api_key=os.environ.get("pinecone_Api_key", ""))
    index_name = os.environ.get("PINECONE_INDEX_NAME", "documents")

    DIMENSION = 1024

    logger.info("Listing indexes")
    existing = {i.name: i for i in pc.list_indexes()}

    if index_name in existing:
        # Delete and recreate if the dimension doesn't match
        current_dim = existing[index_name].dimension
        if current_dim != DIMENSION:
            logger.warning(f"[Pinecone] Index '{index_name}' has dimension {current_dim}, expected {DIMENSION}. Recreating...")
            pc.delete_index(index_name)
            existing.pop(index_name)

    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=os.environ.get("PINECONE_CLOUD", "aws"),
                region=os.environ.get("PINECONE_REGION", "us-east-1"),
            ),
        )
        logger.info(f"[Pinecone] Created index '{index_name}' with dimension {DIMENSION}")

    logger.info(f"Index client created for index '{index_name}'")
    _INDEX_CACHE = pc.Index(index_name)
    return _INDEX_CACHE

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings using the module-level model (loaded once at worker start)."""
    return _EMBED_MODEL.encode(texts, normalize_embeddings=True).tolist()


class PineconeService:

    def index_document(self, doc_id: str, doc_name: str, chunks_meta: list[dict]) -> int:
        """Upsert all chunks for a document. Returns number of vectors upserted.

        chunks_meta: list of {"text": str, "page": int}
        """

        if not chunks_meta:
            return 0

        texts = [c["text"] for c in chunks_meta]
        embeddings = embed_texts(texts)

        vectors = [
            {
                "id": f"{doc_id}-{i}",
                "values": embeddings[i],
                "metadata": {
                    "doc_id":   doc_id,
                    "doc_name": doc_name,
                    "page":     chunks_meta[i].get("page", 0),
                    "text":     texts[i],
                },
            }
            for i in range(len(texts))
        ]

        index = _get_index()
        batch_size = 100
        for start in range(0, len(vectors), batch_size):
            index.upsert(vectors=vectors[start : start + batch_size])

        logger.info(f"[Pinecone] Upserted {len(vectors)} vectors for doc {doc_id}")
        return len(vectors)

    def query(self, doc_ids: list[str], query_vec: list[float], top_k: int = 10) -> list[dict]:
        """Semantic search filtered to selected doc_ids. Returns list of {text, score}."""
        if not doc_ids:
            return []

        index = _get_index()
        results = index.query(
            vector=query_vec,
            top_k=top_k,
            filter={"doc_id": {"$in": doc_ids}},
            include_metadata=True,
        )
        return [
            {
                "text":     m.metadata.get("text", ""),
                "score":    m.score,
                "doc_name": m.metadata.get("doc_name", ""),
                "page":     m.metadata.get("page", 0),
            }
            for m in results.matches
            if m.metadata
        ]

    def delete_document(self, doc_id: str):
        """Delete all vectors belonging to a document."""
        index = _get_index()
        index.delete(filter={"doc_id": doc_id})
        logger.info(f"[Pinecone] Deleted vectors for doc {doc_id}")
