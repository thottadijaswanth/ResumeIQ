import time
from typing import List, Optional
from backend.app.ai.provider import BaseAIProvider
from backend.app.schemas.analysis import CandidateMatchAssessment, RequirementEvidence
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.resume import StructuredResume
from backend.app.utils.logger import logger


class CandidateMatchingAgent:
    """
    Provider-agnostic matching and evidence verification agent.
    Delegates exclusively through BaseAIProvider without knowing whether
    the underlying model runs locally (Ollama), in the cloud (OpenAI-compatible),
    or deterministically (Mock).
    """

    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider

    def evaluate(
        self,
        *,
        candidate_id: str,
        resume: StructuredResume,
        job: StructuredJob,
        relevant_evidence: List[RequirementEvidence],
    ) -> CandidateMatchAssessment:
        start = time.perf_counter()
        try:
            assessment = self.ai_provider.assess_candidate_match(
                candidate_id=candidate_id,
                resume=resume,
                job=job,
                relevant_evidence=relevant_evidence,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                f"CandidateMatchingAgent completed provider={self.ai_provider.provider_name} "
                f"model={self.ai_provider.model_name} matching_duration_ms={duration_ms:.1f} "
                f"recommendation={assessment.recommendation} confidence={assessment.confidence}"
            )
            return assessment
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                f"CandidateMatchingAgent failed provider={self.ai_provider.provider_name} "
                f"model={self.ai_provider.model_name} matching_duration_ms={duration_ms:.1f} "
                f"error={type(exc).__name__}"
            )
            raise

