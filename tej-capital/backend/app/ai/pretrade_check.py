"""Pre-trade advisory checks from LLM. Raises NotConfiguredError if LLM API key not set."""
from app.api.errors import NotConfiguredError
from app.config import get_settings


def _ensure():
    if not get_settings().llm_api_key:
        raise NotConfiguredError(
            "llm",
            "set TEJ_LLM_API_KEY to enable pre-trade advisory checks"
        )


def ask(thesis: str, playbook: str) -> str:
    """Ask LLM for advisory pre-trade sanity checks.

    Args:
        thesis: Trade thesis/rationale
        playbook: Associated playbook or trading rules

    Returns:
        Advisory response string

    Raises:
        NotConfiguredError: If LLM API key is not configured
    """
    _ensure()
    # Real implementation in follow-up commit
