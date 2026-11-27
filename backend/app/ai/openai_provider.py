import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from backend.app.ai.exceptions import (
    AIAuthenticationError,
    AIModelNotFoundError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AIUnavailableError,
)
from backend.app.ai.json_utils import sanitize_error_message
from backend.app.ai.provider import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    Cloud AI provider supporting the standard OpenAI-compatible `/v1` API.
    Works with OpenAI and any OpenAI-compatible inference endpoint via OPENAI_BASE_URL.
    """

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.1,
        timeout: float = 60.0,
        max_retries: int = 2,
        retry_delay: float = 0.1,
        transport: Optional[httpx.BaseTransport] = None,
        async_transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self._temperature = temperature
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_delay = retry_delay
        self._transport = transport
        self._async_transport = async_transport

    @property
    def default_temperature(self) -> float:
        return self._temperature

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        json_mode: bool,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload

    def _extract_response(self, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        choices = data.get("choices") or []
        if not choices or "message" not in choices[0] or "content" not in choices[0]["message"]:
            raise AIProviderError(
                "OpenAI-compatible response missing choices[0].message.content.",
                provider=self.provider_name,
                model=self.model,
            )
        content = choices[0]["message"]["content"]
        usage = data.get("usage") or {}
        clean_usage = {
            k: usage[k]
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            if k in usage
        }
        return str(content or ""), clean_usage

    def _map_http_error(self, exc: Exception) -> AIProviderError:
        if isinstance(exc, AIProviderError):
            return exc
        if isinstance(exc, httpx.TimeoutException):
            return AITimeoutError(
                f"OpenAI-compatible request timed out after {self.timeout}s.",
                provider=self.provider_name,
                model=self.model,
                retryable=False,
            )
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
            return AIUnavailableError(
                f"Cannot connect to OpenAI-compatible API at {self.base_url}.",
                provider=self.provider_name,
                model=self.model,
                retryable=True,
            )
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            detail = sanitize_error_message(
                exc.response.text[:250], secrets=(self.api_key,)
            )
            if status_code in (401, 403):
                return AIAuthenticationError(
                    "Authentication failed with OpenAI-compatible API.",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=status_code,
                    retryable=False,
                )
            if status_code == 429:
                return AIRateLimitError(
                    "Rate limit exceeded by OpenAI-compatible API.",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=status_code,
                    retryable=True,
                )
            if status_code == 404:
                return AIModelNotFoundError(
                    f"Configured cloud model '{self.model}' was not found.",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=status_code,
                    retryable=False,
                )
            if status_code >= 500:
                return AIUnavailableError(
                    f"Cloud AI server error ({status_code}).",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=status_code,
                    retryable=True,
                )
            return AIProviderError(
                f"OpenAI-compatible API error ({status_code}): {detail}",
                provider=self.provider_name,
                model=self.model,
                status_code=status_code,
                retryable=False,
            )
        return AIProviderError(
            f"OpenAI-compatible request failed: {sanitize_error_message(str(exc), secrets=(self.api_key,))}",
            provider=self.provider_name,
            model=self.model,
            retryable=False,
        )

    def _complete_chat_sync(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        json_mode: bool = False,
        operation: str = "generate",
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        payload = self._build_payload(
            messages, temperature=temperature, json_mode=json_mode, max_tokens=max_tokens
        )
        last_err: Optional[AIProviderError] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    return self._extract_response(response.json())
            except Exception as exc:
                mapped = self._map_http_error(exc)
                last_err = mapped
                if mapped.retryable and attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise mapped from exc

        assert last_err is not None
        raise last_err

    async def _complete_chat_async(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        json_mode: bool = False,
        operation: str = "generate",
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        payload = self._build_payload(
            messages, temperature=temperature, json_mode=json_mode, max_tokens=max_tokens
        )
        last_err: Optional[AIProviderError] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, transport=self._async_transport
                ) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    return self._extract_response(response.json())
            except Exception as exc:
                mapped = self._map_http_error(exc)
                last_err = mapped
                if mapped.retryable and attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise mapped from exc

        assert last_err is not None
        raise last_err

    def _interpret_models_response(self, status_code: int) -> Dict[str, Any]:
        if status_code == 200:
            return {
                "provider": self.provider_name,
                "status": "healthy",
                "model": self.model,
                "mode": "cloud",
                "message": "Connected to OpenAI-compatible API",
            }
        if status_code in (401, 403):
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "Authentication failed for OpenAI-compatible API",
            }
        if status_code in (404, 405):
            # Some OpenAI-compatible inference gateways restrict GET /models
            return {
                "provider": self.provider_name,
                "status": "healthy",
                "model": self.model,
                "mode": "cloud",
                "message": "OpenAI-compatible endpoint reachable",
            }
        return {
            "provider": self.provider_name,
            "status": "unavailable",
            "model": self.model,
            "mode": "cloud",
            "message": f"OpenAI-compatible API returned status {status_code}",
        }

    def health_check_sync(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "OPENAI_API_KEY is not configured",
            }
        try:
            with httpx.Client(
                timeout=min(self.timeout, 5.0), transport=self._transport
            ) as client:
                response = client.get(f"{self.base_url}/models", headers=self._headers())
                return self._interpret_models_response(response.status_code)
        except httpx.TimeoutException:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "Timed out connecting to OpenAI-compatible API",
            }
        except Exception:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "Cannot connect to OpenAI-compatible API",
            }

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "OPENAI_API_KEY is not configured",
            }
        try:
            async with httpx.AsyncClient(
                timeout=min(self.timeout, 5.0), transport=self._async_transport
            ) as client:
                response = await client.get(f"{self.base_url}/models", headers=self._headers())
                return self._interpret_models_response(response.status_code)
        except httpx.TimeoutException:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "Timed out connecting to OpenAI-compatible API",
            }
        except Exception:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "cloud",
                "message": "Cannot connect to OpenAI-compatible API",
            }
