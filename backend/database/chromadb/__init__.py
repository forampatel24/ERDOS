"""ChromaDB vector store for historical disasters."""

from backend.database.chromadb.client import get_chroma_client, get_collection
from backend.database.chromadb.embeddings import embed_payload, generate_embedding
from backend.database.chromadb.retrieval import add_disaster, count, search_similars

__all__ = [
    "get_chroma_client",
    "get_collection",
    "embed_payload",
    "generate_embedding",
    "add_disaster",
    "count",
    "search_similars",
]

