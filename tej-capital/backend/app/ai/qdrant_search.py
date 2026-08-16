"""Qdrant vector search for journal entries. Raises NotConfiguredError if Qdrant URL not set."""
from app.api.errors import NotConfiguredError
from app.config import get_settings


def _ensure():
    if not get_settings().qdrant_url:
        raise NotConfiguredError(
            "qdrant",
            "set TEJ_QDRANT_URL + TEJ_LLM_API_KEY (for embeddings) to enable journal search"
        )


def embed_and_index(text: str, metadata: dict) -> str:
    """Embed text and index it in Qdrant with metadata.

    Args:
        text: Text to embed and index
        metadata: Associated metadata (e.g., journal_entry_id, tags)

    Returns:
        Qdrant point ID as string

    Raises:
        NotConfiguredError: If Qdrant is not configured
    """
    _ensure()
    # Real implementation in follow-up commit


def query(text: str, k: int = 10) -> list[dict]:
    """Search Qdrant for similar journal entries.

    Args:
        text: Query text to search for
        k: Number of results to return

    Returns:
        List of dicts with keys: point_id, score, metadata

    Raises:
        NotConfiguredError: If Qdrant is not configured
    """
    _ensure()
    # Real implementation in follow-up commit
