"""AI-generated tearsheet commentary. Raises NotConfiguredError if LLM API key not set."""
from app.api.errors import NotConfiguredError
from app.config import get_settings


def _ensure():
    if not get_settings().llm_api_key:
        raise NotConfiguredError(
            "llm",
            "set TEJ_LLM_API_KEY to enable AI-generated tearsheet commentary"
        )


def draft(tearsheet: dict, journal_entries: list[dict]) -> str:
    """Draft AI-generated prose commentary from tearsheet metrics and journal.

    Args:
        tearsheet: Dictionary with keys like returns, sharpe, max_dd, etc.
        journal_entries: List of journal entry dicts with body, tags, etc.

    Returns:
        Prose commentary string

    Raises:
        NotConfiguredError: If LLM API key is not configured
    """
    _ensure()
    # Real implementation in follow-up commit
