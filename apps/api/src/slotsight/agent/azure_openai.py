"""Azure OpenAI client construction.

**There is no API key anywhere in this module, and no setting to supply one.**

Auth is Microsoft Entra ID via ``DefaultAzureCredential``, which resolves to
your ``az login`` identity in local development and to the Container App's
user-assigned managed identity in Azure. Nothing to store, nothing to rotate,
nothing to leak into a commit. See SECURITY.md.

The credential is process-wide and cached. Creating a fresh
``DefaultAzureCredential`` per request would re-run the whole credential chain
and mint a new token on every call.
"""

from __future__ import annotations

import logging

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from slotsight.config import Settings

logger = logging.getLogger(__name__)

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"

_credential: DefaultAzureCredential | None = None
_client: AsyncAzureOpenAI | None = None


class AzureOpenAINotConfiguredError(RuntimeError):
    """Raised when a chat request arrives without Azure OpenAI configured.

    Carries actionable remediation text rather than a bare failure, because
    this is the single most likely thing to go wrong for someone who just
    cloned the repository.
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            "Azure OpenAI is required for /api/chat but is not configured. "
            f"Missing: {', '.join(missing)}. "
            "Set these in .env (copy .env.example), then run `az login` and ensure "
            "your account holds the 'Cognitive Services OpenAI User' role on the "
            "resource. Note that the analytics, dashboard, and recommendation "
            "endpoints do NOT require this and work without it. "
            "See docs/troubleshooting.md."
        )


def ensure_configured(settings: Settings) -> None:
    """Raise a helpful error if the chat path cannot possibly work."""
    missing: list[str] = []
    if not settings.azure_openai_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not settings.azure_openai_deployment:
        missing.append("AZURE_OPENAI_DEPLOYMENT")
    if missing:
        raise AzureOpenAINotConfiguredError(missing)


def get_client(settings: Settings) -> AsyncAzureOpenAI:
    """Return the process-wide Azure OpenAI client, creating it on first use."""
    global _credential, _client

    ensure_configured(settings)

    if _client is None:
        _credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(_credential, COGNITIVE_SERVICES_SCOPE)
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint or "",
            azure_ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
            max_retries=2,
            timeout=60.0,
        )
        logger.info(
            "Azure OpenAI client created (deployment=%s, auth=entra)",
            settings.azure_openai_deployment,
        )

    return _client


async def close_client() -> None:
    """Release the client and credential on shutdown."""
    global _credential, _client
    if _client is not None:
        await _client.close()
        _client = None
    if _credential is not None:
        await _credential.close()
        _credential = None


__all__ = [
    "COGNITIVE_SERVICES_SCOPE",
    "AzureOpenAINotConfiguredError",
    "close_client",
    "ensure_configured",
    "get_client",
]
