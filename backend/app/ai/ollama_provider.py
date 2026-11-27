import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from backend.app.ai.exceptions import (
    AIModelNotFoundError,
    AIProviderError,
    AITimeoutError,
    AIUnavailableError,
)
from backend.app.ai.json_utils import sanitize_error_message
from backend.app.ai.provider import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    Local/offline AI provider communicating with the Ollama HTTP API.
    Never makes external cloud calls.
    """

    provider_name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        temperature: float = 0.0,
        timeout: float = 120.0,
        max_retries: int = 2,
        retry_delay: float = 0.1,
        think: Optional[bool] = False,
        transport: Optional[httpx.BaseTransport] = None,
        async_transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_name = model
        self._temperature = temperature
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.retry_delay = retry_delay
        self.think = think
        self._transport = transport
        self._async_transport = async_transport

    @property
    def default_temperature(self) -> float:
        return self._temperature

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
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 900,
            },
        }
        if json_mode:
            payload["format"] = "json"
        if self.think is not None:
            payload["think"] = self.think
        return payload

    def _extract_response(self, data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        if isinstance(data, dict) and data.get("error"):
            err_msg = str(data["error"])
            if "not found" in err_msg.lower():
                raise AIModelNotFoundError(
                    f"Ollama is running but model '{self.model}' is not installed. "
                    "Please install the configured model.",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=404,
                )
            raise AIProviderError(
                f"Ollama returned error: {err_msg}",
                provider=self.provider_name,
                model=self.model,
            )

        message = data.get("message") or {}
        content = message.get("content")
        if content is None:
            content = data.get("response", "")

        usage: Dict[str, Any] = {}
        if "prompt_eval_count" in data:
            usage["prompt_tokens"] = data["prompt_eval_count"]
        if "eval_count" in data:
            usage["completion_tokens"] = data["eval_count"]
        if usage:
            usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

        return str(content), usage

    def _map_http_error(self, exc: Exception) -> AIProviderError:
        if isinstance(exc, AIProviderError):
            return exc
        if isinstance(exc, httpx.TimeoutException):
            return AITimeoutError(
                f"Ollama request timed out after {self.timeout}s for model '{self.model}'.",
                provider=self.provider_name,
                model=self.model,
                retryable=False,
            )
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
            return AIUnavailableError(
                f"Cannot connect to Ollama at {self.base_url}.",
                provider=self.provider_name,
                model=self.model,
                retryable=True,
            )
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            detail = ""
            try:
                body = exc.response.json()
                detail = str(body.get("error") or body.get("message") or "")
            except Exception:
                detail = exc.response.text[:200]
            detail = sanitize_error_message(detail)

            if status_code == 404 or "not found" in detail.lower():
                return AIModelNotFoundError(
                    f"Ollama is running but model '{self.model}' is not installed. "
                    "Please install the configured model.",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=status_code,
                    retryable=False,
                )
            if status_code >= 500:
                return AIUnavailableError(
                    f"Ollama server error ({status_code}): {detail}",
                    provider=self.provider_name,
                    model=self.model,
                    status_code=status_code,
                    retryable=True,
                )
            return AIProviderError(
                f"Ollama HTTP error ({status_code}): {detail}",
                provider=self.provider_name,
                model=self.model,
                status_code=status_code,
                retryable=False,
            )
        return AIProviderError(
            f"Ollama request failed: {sanitize_error_message(str(exc))}",
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
        last_err: Optional[AIProviderError] = None

        for attempt in range(self.max_retries + 1):
            payload = self._build_payload(
                messages, temperature=temperature, json_mode=json_mode, max_tokens=max_tokens
            )
            try:
                with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                    response = client.post(f"{self.base_url}/api/chat", json=payload)
                    if (
                        response.status_code == 400
                        and self.think is not None
                        and "think" in response.text.lower()
                    ):
                        # Model does not support Ollama `think` parameter; disable and retry immediately
                        self.think = None
                        payload.pop("think", None)
                        response = client.post(f"{self.base_url}/api/chat", json=payload)
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
        last_err: Optional[AIProviderError] = None

        for attempt in range(self.max_retries + 1):
            payload = self._build_payload(
                messages, temperature=temperature, json_mode=json_mode, max_tokens=max_tokens
            )
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, transport=self._async_transport
                ) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    if (
                        response.status_code == 400
                        and self.think is not None
                        and "think" in response.text.lower()
                    ):
                        self.think = None
                        payload.pop("think", None)
                        response = await client.post(f"{self.base_url}/api/chat", json=payload)
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

    def _is_model_installed(self, tags_payload: Dict[str, Any]) -> bool:
        models = tags_payload.get("models") or []
        installed_names = set()
        for entry in models:
            if isinstance(entry, dict):
                for key in ("name", "model"):
                    val = entry.get(key)
                    if val:
                        installed_names.add(str(val))
        if self.model in installed_names:
            return True
        if ":" not in self.model and f"{self.model}:latest" in installed_names:
            return True
        return False

    def _interpret_tags_health(self, tags_payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_model_installed(tags_payload):
            return {
                "provider": self.provider_name,
                "status": "healthy",
                "model": self.model,
                "mode": "local",
                "message": f"Connected to Ollama ({self.model})",
            }
        return {
            "provider": self.provider_name,
            "status": "unavailable",
            "model": self.model,
            "mode": "local",
            "message": (
                f"Ollama is running but model '{self.model}' is not installed. "
                "Please install the configured model."
            ),
        }

    def health_check_sync(self) -> Dict[str, Any]:
        try:
            with httpx.Client(
                timeout=min(self.timeout, 5.0), transport=self._transport
            ) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return self._interpret_tags_health(response.json())
        except httpx.TimeoutException:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "local",
                "message": "Timed out connecting to Ollama",
            }
        except Exception:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "local",
                "message": "Cannot connect to Ollama",
            }

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=min(self.timeout, 5.0), transport=self._async_transport
            ) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return self._interpret_tags_health(response.json())
        except httpx.TimeoutException:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "local",
                "message": "Timed out connecting to Ollama",
            }
        except Exception:
            return {
                "provider": self.provider_name,
                "status": "unavailable",
                "model": self.model,
                "mode": "local",
                "message": "Cannot connect to Ollama",
            }

