from fastapi import HTTPException


class NotConfiguredError(Exception):
    """Raised by integrations (broker adapters, Temporal, Telegram, Qdrant, LLM,
    PDF export) when their credentials or binaries are not present. Mapped to
    HTTP 501 by the exception handler."""

    def __init__(self, integration: str, hint: str):
        self.integration = integration
        self.hint = hint
        super().__init__(f"{integration}: {hint}")


def not_configured_handler(_request, exc: NotConfiguredError):
    return HTTPException(status_code=501, detail={
        "error": "not_configured",
        "integration": exc.integration,
        "hint": exc.hint,
    })
