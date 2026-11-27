from pathlib import Path
from typing import Any, Callable, Optional, Tuple, TypeVar
from backend.app.ai.embeddings import (
    BaseEmbeddingProvider,
    CloudEmbeddingProvider,
    LocalDeterministicEmbeddingProvider,
    LocalEmbeddingProvider,
    OpenAIEmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
)
from backend.app.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIModelNotFoundError,
    AIProviderError,
    AIRateLimitError,
    AIStructuredOutputError,
    AITimeoutError,
    AIUnavailableError,
)
from backend.app.ai.matching_agent import CandidateMatchingAgent
from backend.app.ai.mock_provider import MockAIProvider
from backend.app.ai.ollama_provider import OllamaProvider
from backend.app.ai.openai_provider import OpenAIProvider
from backend.app.ai.provider import BaseAIProvider, BaseLLMProvider
from backend.app.config import settings
from backend.app.utils.logger import logger

T = TypeVar("T")

SUPPORTED_AI_PROVIDERS = ("auto", "ollama", "openai", "mock")


def _build_ollama_provider() -> OllamaProvider:
    return OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout=settings.OLLAMA_TIMEOUT,
        max_retries=settings.OLLAMA_MAX_RETRIES,
        think=settings.OLLAMA_THINK,
    )


def _build_openai_provider() -> OpenAIProvider:
    api_key = settings.get_openai_api_key()
    if not api_key:
        raise AIConfigurationError(
            "OPENAI_API_KEY is required when AI_PROVIDER=openai."
        )
    return OpenAIProvider(
        api_key=api_key,
        model=settings.get_openai_model(),
        base_url=settings.OPENAI_BASE_URL,
        temperature=settings.OPENAI_TEMPERATURE,
        timeout=settings.OPENAI_TIMEOUT,
        max_retries=settings.OPENAI_MAX_RETRIES,
    )


def _resolve_auto_provider() -> BaseAIProvider:
    """
    Automatic online/offline provider resolution:
    - If OpenAI key is configured and endpoint is reachable online -> OpenAIProvider.
    - Otherwise (offline / unreachable / no key) -> check local Ollama; if healthy -> OllamaProvider.
    - Never silently substitutes MockAIProvider.
    """
    if settings.get_openai_api_key():
        openai_provider = _build_openai_provider()
        openai_health = openai_provider.health_check_sync()
        if openai_health.get("status") == "healthy":
            return openai_provider

    ollama_provider = _build_ollama_provider()
    ollama_health = ollama_provider.health_check_sync()
    if ollama_health.get("status") == "healthy":
        return ollama_provider

    if settings.get_openai_api_key():
        return _build_openai_provider()
    return ollama_provider


def build_ai_provider(provider_name: str) -> BaseAIProvider:
    """Instantiate a concrete AI provider for the given provider name."""
    normalized = (provider_name or "").strip().lower()
    if normalized == "auto":
        return _resolve_auto_provider()
    if normalized == "ollama":
        return _build_ollama_provider()
    if normalized == "openai":
        return _build_openai_provider()
    if normalized == "mock":
        return MockAIProvider()

    raise AIConfigurationError(
        f"Unsupported AI_PROVIDER: '{provider_name}'. "
        f"Supported providers: {', '.join(SUPPORTED_AI_PROVIDERS)}."
    )


def get_ai_provider() -> BaseAIProvider:
    """Resolve the active AI provider strictly from environment configuration."""
    return build_ai_provider(settings.AI_PROVIDER)


def get_fallback_ai_provider(primary_provider_name: str) -> Optional[BaseAIProvider]:
    """
    Resolve configured fallback provider if AI_FALLBACK_ENABLED=true.
    Enforces privacy: never silently falls back from local Ollama to cloud OpenAI
    unless AI_ALLOW_CLOUD_FALLBACK is explicitly True.
    """
    if not settings.AI_FALLBACK_ENABLED or not settings.AI_FALLBACK_PROVIDER:
        return None

    primary = (primary_provider_name or "").strip().lower()
    fallback = settings.AI_FALLBACK_PROVIDER.strip().lower()

    if fallback == primary:
        return None

    if primary == "ollama" and fallback == "openai" and not settings.AI_ALLOW_CLOUD_FALLBACK:
        logger.warning(
            "Blocked silent fallback from local 'ollama' to cloud 'openai' to preserve candidate privacy."
        )
        return None

    return build_ai_provider(fallback)


def run_with_ai_fallback(
    operation_name: str,
    fn: Callable[[BaseAIProvider], T],
    *,
    primary_provider: Optional[BaseAIProvider] = None,
) -> Tuple[T, bool]:
    """
    Execute an AI operation using the configured BaseAIProvider, applying
    configured fallback behavior if enabled and permitted.
    Returns (result, fallback_used).
    """
    provider = primary_provider or get_ai_provider()
    try:
        return fn(provider), False
    except Exception as primary_exc:
        fallback_provider = get_fallback_ai_provider(provider.provider_name)
        if fallback_provider is None:
            logger.error(
                f"AI operation={operation_name} failed provider={provider.provider_name} "
                f"model={provider.model_name} fallback_used=false error={type(primary_exc).__name__}"
            )
            raise

        logger.warning(
            f"AI operation={operation_name} primary_failed provider={provider.provider_name} "
            f"fallback_provider={fallback_provider.provider_name} fallback_used=true "
            f"error={type(primary_exc).__name__}"
        )
        return fn(fallback_provider), True


def set_ai_provider_mode(provider_name: str, persist_env: bool = True) -> dict[str, Any]:
    """Switch active AI_PROVIDER mode at runtime and optionally update root .env."""
    normalized = (provider_name or "").strip().lower()
    if normalized not in SUPPORTED_AI_PROVIDERS:
        raise AIConfigurationError(
            f"Unsupported AI_PROVIDER: '{provider_name}'. "
            f"Supported providers: {', '.join(SUPPORTED_AI_PROVIDERS)}."
        )
    settings.AI_PROVIDER = normalized

    if persist_env:
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            replaced = False
            for idx, line in enumerate(lines):
                if line.strip().startswith("AI_PROVIDER="):
                    lines[idx] = f"AI_PROVIDER={normalized}"
                    replaced = True
                    break
            if not replaced:
                lines.append(f"AI_PROVIDER={normalized}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return get_ai_health_status()


def get_ai_health_status() -> dict[str, Any]:
    """Check health of the configured AI provider without leaking secrets."""
    configured = (settings.AI_PROVIDER or "").strip().lower()
    mode_map = {"ollama": "local", "openai": "cloud", "mock": "mock"}

    fallback_provider = (
        settings.AI_FALLBACK_PROVIDER.strip().lower()
        if settings.AI_FALLBACK_ENABLED and settings.AI_FALLBACK_PROVIDER
        else None
    )

    try:
        provider = get_ai_provider()
        status_payload = provider.health_check_sync()
    except AIConfigurationError as exc:
        model = (
            settings.OLLAMA_MODEL
            if configured == "ollama"
            else (settings.get_openai_model() if configured == "openai" else "")
        )
        status_payload = {
            "provider": configured or "unknown",
            "status": "unavailable",
            "model": model,
            "mode": mode_map.get(configured, "unknown"),
            "message": str(exc),
        }
    except Exception as exc:
        status_payload = {
            "provider": configured or "unknown",
            "status": "unavailable",
            "model": "",
            "mode": mode_map.get(configured, "unknown"),
            "message": f"Health check failed: {type(exc).__name__}",
        }

    return {
        **status_payload,
        "configured_provider": configured,
        "available": status_payload.get("status") == "healthy",
        "embedding_provider": (settings.EMBEDDING_PROVIDER or "local").strip().lower(),
        "fallback_enabled": settings.AI_FALLBACK_ENABLED,
        "fallback_provider": fallback_provider,
    }


__all__ = [
    "AIAuthenticationError",
    "AIConfigurationError",
    "AIModelNotFoundError",
    "AIProviderError",
    "AIRateLimitError",
    "AIStructuredOutputError",
    "AITimeoutError",
    "AIUnavailableError",
    "BaseAIProvider",
    "BaseEmbeddingProvider",
    "BaseLLMProvider",
    "CandidateMatchingAgent",
    "CloudEmbeddingProvider",
    "LocalDeterministicEmbeddingProvider",
    "LocalEmbeddingProvider",
    "MockAIProvider",
    "OllamaProvider",
    "OpenAIEmbeddingProvider",
    "OpenAIProvider",
    "SUPPORTED_AI_PROVIDERS",
    "build_ai_provider",
    "cosine_similarity",
    "get_ai_health_status",
    "get_ai_provider",
    "get_embedding_provider",
    "get_fallback_ai_provider",
    "run_with_ai_fallback",
    "set_ai_provider_mode",
]
