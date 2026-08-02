"""
Retrieval over Lenny's Podcast transcripts, backed by Qdrant.

Uses qdrant-client's built-in FastEmbed integration (`.add()` / `.query()`),
so embeddings are generated automatically with a small local ONNX model —
no separate embedding service or API key required, even when Qdrant itself
is a remote/cloud cluster.

Run `python ingest.py` once (see backend/ingest.py) to build the index
before starting the API — see README.md.
"""
from qdrant_client import QdrantClient
from .config import settings

_client = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        if settings.qdrant_url:
            # Qdrant Cloud or a remote/docker Qdrant instance
            _client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )
        else:
            # Local, file-backed Qdrant — zero setup, good for quick demos
            _client = QdrantClient(path=settings.qdrant_local_path)
    return _client


def _collection_exists(client: QdrantClient) -> bool:
    try:
        return client.collection_exists(settings.qdrant_collection)
    except Exception:
        return False


def query_transcripts(query: str, k: int = 5):
    """Returns a list of {text, source} dicts, best matches first."""
    client = _get_client()
    if not _collection_exists(client):
        return []

    results = client.query(
        collection_name=settings.qdrant_collection,
        query_text=query,
        limit=k,
    )
    out = []
    for point in results:
        meta = point.metadata or {}
        out.append({
            "text": point.document or meta.get("document", ""),
            "source": meta.get("source", "unknown episode"),
        })
    return out


def format_context(chunks) -> str:
    if not chunks:
        return "(No transcript context was retrieved — the knowledge base may be empty. Run ingest.py.)"
    parts = []
    for c in chunks:
        parts.append(f"[Source: {c['source']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)
