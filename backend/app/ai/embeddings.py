import hashlib
import math
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from backend.app.ai.exceptions import AIConfigurationError, AIProviderError
from backend.app.ai.json_utils import sanitize_error_message
from backend.app.config import settings
from backend.app.utils.logger import logger


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class BaseEmbeddingProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass


class LocalDeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """
    Offline deterministic pseudo-semantic embedding engine with configurable dimensions (default 1536).
    Uses MD5 feature hashing with word unigrams/bigrams and L2 normalization.
    Requires zero network calls.
    """

    provider_name = "local"

    def __init__(self, dim: int = 1536):
        self.dim = dim

    def get_embedding(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = text.lower().split()
        if not tokens:
            return vec

        ngrams = list(tokens)
        for i in range(len(tokens) - 1):
            ngrams.append(f"{tokens[i]}_{tokens[i + 1]}")

        for ngram in ngrams:
            h = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 3) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embedding(t) for t in texts]


LocalEmbeddingProvider = LocalDeterministicEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Cloud embedding provider using OpenAI-compatible `/v1/embeddings` API."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }
        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                res = client.post(
                    f"{self.base_url}/embeddings", headers=headers, json=payload
                )
                res.raise_for_status()
                data = res.json()
                return [item["embedding"] for item in data["data"]]
        except Exception as exc:
            safe_msg = sanitize_error_message(str(exc), secrets=(self.api_key,))
            logger.error(f"Embedding API error (model={self.model}): {safe_msg}")
            raise AIProviderError(
                f"Embedding request failed: {safe_msg}",
                provider=self.provider_name,
                model=self.model,
            ) from exc

    def get_embedding(self, text: str) -> List[float]:
        return self.get_embeddings([text])[0]


CloudEmbeddingProvider = OpenAIEmbeddingProvider


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = (settings.EMBEDDING_PROVIDER or "local").strip().lower()
    if provider in ("local", "mock"):
        return LocalDeterministicEmbeddingProvider(dim=settings.EMBEDDING_DIMENSIONS)
    if provider == "openai":
        api_key = settings.get_embedding_api_key()
        if not api_key:
            raise AIConfigurationError(
                "EMBEDDING_API_KEY (or OPENAI_API_KEY) is required when EMBEDDING_PROVIDER=openai."
            )
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=settings.EMBEDDING_MODEL,
            base_url=settings.get_embedding_base_url(),
            timeout=settings.EMBEDDING_TIMEOUT,
        )
    raise AIConfigurationError(
        f"Unsupported EMBEDDING_PROVIDER: '{settings.EMBEDDING_PROVIDER}'. "
        "Supported providers: 'local', 'openai', 'mock'."
    )
