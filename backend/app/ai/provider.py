import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union
from pydantic import BaseModel
from backend.app.ai.exceptions import AIStructuredOutputError
from backend.app.ai.json_utils import (
    extract_json_payload,
    schema_dict_for_model,
    validate_structured_payload,
)
from backend.app.ai.prompts import (
    CANDIDATE_MATCHING_SYSTEM_PROMPT,
    CANDIDATE_RERANK_SYSTEM_PROMPT,
    COVER_LETTER_SYSTEM_PROMPT,
    JOB_EXTRACTION_SYSTEM_PROMPT,
    RECOMMENDATION_SYSTEM_PROMPT,
    RESUME_EXTRACTION_SYSTEM_PROMPT,
    STRUCTURED_JSON_CORRECTION_INSTRUCTION,
    TAILORED_RESUME_SYSTEM_PROMPT,
)
from backend.app.config import settings
from backend.app.schemas.analysis import (
    CandidateMatchAssessment,
    CandidateRerankResult,
    CoverLetterResponse,
    RecommendationItem,
    RequirementEvidence,
    TailorResumeResponse,
)
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.resume import StructuredResume
from backend.app.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationItem]


class BaseAIProvider(ABC):
    """Abstract interface implemented by all ResumeIQ AI providers."""

    provider_name: str = "base"
    model_name: str = ""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate free-form text asynchronously."""
        pass

    @abstractmethod
    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate free-form text synchronously."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Union[Dict[str, Any], Type[T]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """Generate structured JSON output validated against a schema asynchronously."""
        pass

    @abstractmethod
    def generate_structured_sync(
        self,
        prompt: str,
        schema: Union[Dict[str, Any], Type[T]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """Generate structured JSON output validated against a schema synchronously."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider connectivity and configured model availability asynchronously."""
        pass

    @abstractmethod
    def health_check_sync(self) -> Dict[str, Any]:
        """Check provider connectivity and configured model availability synchronously."""
        pass

    @abstractmethod
    def extract_structured_resume(self, raw_text: str) -> StructuredResume:
        """Extract candidate information into StructuredResume schema."""
        pass

    @abstractmethod
    def extract_structured_job(self, raw_text: str) -> StructuredJob:
        """Extract job description details into StructuredJob schema."""
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        matching_data: Dict[str, Any],
    ) -> List[RecommendationItem]:
        """Generate categorized, actionable resume improvement recommendations."""
        pass

    @abstractmethod
    def tailor_resume(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        matching_data: Dict[str, Any],
    ) -> TailorResumeResponse:
        """Generate tailored bullet points, reordered skills, and tailored summary."""
        pass

    @abstractmethod
    def generate_cover_letter(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        tone: str = "Professional",
        custom_notes: Optional[str] = None,
    ) -> CoverLetterResponse:
        """Generate a tailored cover letter without hallucinating experience."""
        pass

    @abstractmethod
    def assess_candidate_match(
        self,
        candidate_id: str,
        resume: StructuredResume,
        job: StructuredJob,
        relevant_evidence: List[RequirementEvidence],
    ) -> CandidateMatchAssessment:
        """Evaluate candidate fit with evidence verification and zero hallucination."""
        pass

    @abstractmethod
    def rerank_candidate(
        self,
        candidate_summary: Dict[str, Any],
        job_summary: Dict[str, Any],
    ) -> CandidateRerankResult:
        """Fast, concise AI reranking on pre-shortlisted candidate evidence."""
        pass


class BaseLLMProvider(BaseAIProvider, ABC):
    """
    Shared business-level prompt construction, structured JSON validation,
    retry-with-correction logic, and safe telemetry for all LLM-backed providers
    (OllamaProvider, OpenAIProvider, etc.).
    """

    @abstractmethod
    def _complete_chat_sync(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        json_mode: bool = False,
        operation: str = "generate",
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Execute synchronous chat completion and return (content, token_usage)."""
        pass

    @abstractmethod
    async def _complete_chat_async(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        json_mode: bool = False,
        operation: str = "generate",
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Execute asynchronous chat completion and return (content, token_usage)."""
        pass

    @property
    def default_temperature(self) -> float:
        return 0.0

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        sys_parts: List[str] = []
        if system_prompt:
            sys_parts.append(system_prompt.strip())
        if schema_dict is not None:
            sys_parts.append(
                "Return ONLY valid JSON matching this exact structure (preserve types and keys):\n"
                + json.dumps(schema_dict, separators=(",", ":"))
            )
        if sys_parts:
            messages.append({"role": "system", "content": "\n\n".join(sys_parts)})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _resolve_schema(
        self, schema: Union[Dict[str, Any], Type[T]]
    ) -> Tuple[Dict[str, Any], Optional[Type[T]]]:
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema_dict_for_model(schema), schema
        return schema, None

    def _parse_and_validate(
        self,
        raw_content: str,
        schema_model: Optional[Type[T]],
        schema_dict: Dict[str, Any],
    ) -> Any:
        parsed = extract_json_payload(raw_content)
        if schema_model is not None:
            # Handle providers returning bare list when RecommendationListResponse expected
            if schema_model is RecommendationListResponse and isinstance(parsed, list):
                parsed = {"recommendations": parsed}
            return validate_structured_payload(parsed, schema_model)

        if not isinstance(parsed, dict) and schema_dict.get("type") == "object":
            raise ValueError("Expected JSON object matching schema.")
        if isinstance(parsed, dict):
            required_keys = schema_dict.get("required") or []
            missing = [k for k in required_keys if k not in parsed]
            if missing:
                raise ValueError(f"Missing required JSON fields: {', '.join(missing)}")
        return parsed

    def _log_telemetry(
        self,
        *,
        operation: str,
        duration_ms: float,
        success: bool,
        token_usage: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        usage_str = f" tokens={token_usage}" if token_usage else ""
        status_str = "success" if success else f"failure error={error}"
        logger.info(
            f"AI operation={operation} provider={self.provider_name} "
            f"model={self.model_name} duration_ms={duration_ms:.1f} "
            f"status={status_str}{usage_str}"
        )

    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        temp = self.default_temperature if temperature is None else temperature
        messages = self._build_messages(prompt, system_prompt=system_prompt)
        start = time.perf_counter()
        try:
            content, usage = self._complete_chat_sync(
                messages, temperature=temp, json_mode=False, operation="generate"
            )
            self._log_telemetry(
                operation="generate",
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                token_usage=usage,
            )
            return content
        except Exception as exc:
            self._log_telemetry(
                operation="generate",
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=type(exc).__name__,
            )
            raise

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        temp = self.default_temperature if temperature is None else temperature
        messages = self._build_messages(prompt, system_prompt=system_prompt)
        start = time.perf_counter()
        try:
            content, usage = await self._complete_chat_async(
                messages, temperature=temp, json_mode=False, operation="generate"
            )
            self._log_telemetry(
                operation="generate",
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                token_usage=usage,
            )
            return content
        except Exception as exc:
            self._log_telemetry(
                operation="generate",
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=type(exc).__name__,
            )
            raise

    def generate_structured_sync(
        self,
        prompt: str,
        schema: Union[Dict[str, Any], Type[T]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        schema_dict, schema_model = self._resolve_schema(schema)
        temp = self.default_temperature if temperature is None else temperature
        messages = self._build_messages(prompt, system_prompt=system_prompt, schema_dict=schema_dict)
        operation = schema_model.__name__ if schema_model else "generate_structured"
        start = time.perf_counter()

        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                content, usage = self._complete_chat_sync(
                    messages,
                    temperature=temp,
                    json_mode=True,
                    operation=operation,
                    max_tokens=max_tokens,
                )
                validated = self._parse_and_validate(content, schema_model, schema_dict)
                self._log_telemetry(
                    operation=operation,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    success=True,
                    token_usage=usage,
                )
                return validated
            except (ValueError, json.JSONDecodeError) as parse_exc:
                last_error = parse_exc
                if attempt == 0:
                    messages = messages + [
                        {
                            "role": "user",
                            "content": STRUCTURED_JSON_CORRECTION_INSTRUCTION.format(
                                error=str(parse_exc)
                            ),
                        }
                    ]
                    continue
            except Exception as exc:
                self._log_telemetry(
                    operation=operation,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    success=False,
                    error=type(exc).__name__,
                )
                raise

        self._log_telemetry(
            operation=operation,
            duration_ms=(time.perf_counter() - start) * 1000,
            success=False,
            error="AIStructuredOutputError",
        )
        raise AIStructuredOutputError(
            f"Provider '{self.provider_name}' returned invalid structured output: {last_error}",
            provider=self.provider_name,
            model=self.model_name,
        ) from last_error

    async def generate_structured(
        self,
        prompt: str,
        schema: Union[Dict[str, Any], Type[T]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        schema_dict, schema_model = self._resolve_schema(schema)
        temp = self.default_temperature if temperature is None else temperature
        messages = self._build_messages(prompt, system_prompt=system_prompt, schema_dict=schema_dict)
        operation = schema_model.__name__ if schema_model else "generate_structured"
        start = time.perf_counter()

        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                content, usage = await self._complete_chat_async(
                    messages, temperature=temp, json_mode=True, operation=operation
                )
                validated = self._parse_and_validate(content, schema_model, schema_dict)
                self._log_telemetry(
                    operation=operation,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    success=True,
                    token_usage=usage,
                )
                return validated
            except (ValueError, json.JSONDecodeError) as parse_exc:
                last_error = parse_exc
                if attempt == 0:
                    messages = messages + [
                        {
                            "role": "user",
                            "content": STRUCTURED_JSON_CORRECTION_INSTRUCTION.format(
                                error=str(parse_exc)
                            ),
                        }
                    ]
                    continue
            except Exception as exc:
                self._log_telemetry(
                    operation=operation,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    success=False,
                    error=type(exc).__name__,
                )
                raise

        self._log_telemetry(
            operation=operation,
            duration_ms=(time.perf_counter() - start) * 1000,
            success=False,
            error="AIStructuredOutputError",
        )
        raise AIStructuredOutputError(
            f"Provider '{self.provider_name}' returned invalid structured output: {last_error}",
            provider=self.provider_name,
            model=self.model_name,
        ) from last_error

    # =========================================================================
    # Provider-independent domain methods (shared across Ollama & OpenAI)
    # =========================================================================

    def extract_structured_resume(self, raw_text: str) -> StructuredResume:
        return self.generate_structured_sync(
            prompt=f"Resume Text:\n{raw_text}",
            schema=StructuredResume,
            system_prompt=RESUME_EXTRACTION_SYSTEM_PROMPT,
        )

    def extract_structured_job(self, raw_text: str) -> StructuredJob:
        return self.generate_structured_sync(
            prompt=f"Job Posting Text:\n{raw_text}",
            schema=StructuredJob,
            system_prompt=JOB_EXTRACTION_SYSTEM_PROMPT,
        )

    def generate_recommendations(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        matching_data: Dict[str, Any],
    ) -> List[RecommendationItem]:
        user_prompt = (
            f"Candidate Resume JSON:\n{resume.model_dump_json()}\n\n"
            f"Job Description JSON:\n{job.model_dump_json()}\n\n"
            f"Match Breakdown:\n{json.dumps(matching_data)}"
        )
        result: RecommendationListResponse = self.generate_structured_sync(
            prompt=user_prompt,
            schema=RecommendationListResponse,
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
        )
        return result.recommendations

    def tailor_resume(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        matching_data: Dict[str, Any],
    ) -> TailorResumeResponse:
        user_prompt = (
            f"Candidate Resume JSON:\n{resume.model_dump_json()}\n\n"
            f"Job Description JSON:\n{job.model_dump_json()}\n\n"
            f"Missing Skills:\n{json.dumps(matching_data.get('missing_required_skills', []))}"
        )
        return self.generate_structured_sync(
            prompt=user_prompt,
            schema=TailorResumeResponse,
            system_prompt=TAILORED_RESUME_SYSTEM_PROMPT,
        )

    def generate_cover_letter(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        tone: str = "Professional",
        custom_notes: Optional[str] = None,
    ) -> CoverLetterResponse:
        user_prompt = (
            f"Candidate Resume JSON:\n{resume.model_dump_json()}\n\n"
            f"Job Description JSON:\n{job.model_dump_json()}\n\n"
            f"Tone: {tone}\nAdditional Notes: {custom_notes or 'None'}"
        )
        return self.generate_structured_sync(
            prompt=user_prompt,
            schema=CoverLetterResponse,
            system_prompt=COVER_LETTER_SYSTEM_PROMPT,
        )

    def assess_candidate_match(
        self,
        candidate_id: str,
        resume: StructuredResume,
        job: StructuredJob,
        relevant_evidence: List[RequirementEvidence],
    ) -> CandidateMatchAssessment:
        user_prompt = (
            f"Candidate ID: {candidate_id}\n\n"
            f"Job Profile JSON:\n{job.model_dump_json()}\n\n"
            f"Candidate Profile JSON:\n{resume.model_dump_json()}\n\n"
            f"Retrieved Semantic Evidence:\n"
            f"{json.dumps([item.model_dump() for item in relevant_evidence])}"
        )
        assessment: CandidateMatchAssessment = self.generate_structured_sync(
            prompt=user_prompt,
            schema=CandidateMatchAssessment,
            system_prompt=CANDIDATE_MATCHING_SYSTEM_PROMPT,
        )
        if not assessment.candidate_id:
            assessment.candidate_id = candidate_id
        assessment.provider = self.provider_name
        assessment.model = self.model_name
        return assessment

    def rerank_candidate(
        self,
        candidate_summary: Dict[str, Any],
        job_summary: Dict[str, Any],
    ) -> CandidateRerankResult:
        user_prompt = (
            f"Job Summary:\n{json.dumps(job_summary, separators=(',', ':'))}\n\n"
            f"Candidate Evidence Summary:\n{json.dumps(candidate_summary, separators=(',', ':'))}"
        )
        return self.generate_structured_sync(
            prompt=user_prompt,
            schema=CandidateRerankResult,
            system_prompt=CANDIDATE_RERANK_SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=settings.AI_RERANK_MAX_TOKENS,
        )
