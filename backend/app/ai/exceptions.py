from typing import Optional


class AIConfigurationError(ValueError):
    """Raised when AI or embedding configuration is invalid or incomplete."""


class AIProviderError(RuntimeError):
    """Base error raised by AI providers."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retryable = retryable


class AIUnavailableError(AIProviderError):
    """Raised when the AI provider endpoint cannot be reached or is unavailable."""


class AITimeoutError(AIProviderError):
    """Raised when an AI provider request times out."""


class AIAuthenticationError(AIProviderError):
    """Raised when cloud API authentication fails."""


class AIRateLimitError(AIProviderError):
    """Raised when the AI provider enforces a rate limit."""


class AIModelNotFoundError(AIProviderError):
    """Raised when the configured model is not installed or unavailable."""


class AIStructuredOutputError(AIProviderError):
    """Raised when the AI response cannot be parsed or validated into the expected schema."""

