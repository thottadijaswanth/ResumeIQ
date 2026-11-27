import time
from typing import Tuple, List, Optional
from backend.app.config import settings
from backend.app.schemas.resume import StructuredResume
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.analysis import (
    AnalysisResultData,
    CandidateMatchAssessment,
    RecommendationItem,
)
from backend.app.matching.skill_matcher import SkillMatcher
from backend.app.matching.experience_matcher import ExperienceMatcher
from backend.app.matching.semantic_matcher import SemanticMatcher
from backend.app.matching.education_matcher import EducationMatcher
from backend.app.matching.ats_analyzer import ATSAnalyzer
from backend.app.ai import CandidateMatchingAgent, run_with_ai_fallback
from backend.app.utils.logger import logger


class ScoringEngine:
    @classmethod
    def analyze_resume_against_job(
        cls,
        resume: StructuredResume,
        job: StructuredJob,
        raw_resume_text: str = "",
        candidate_id: str = "",
    ) -> Tuple[AnalysisResultData, List[RecommendationItem]]:
        """
        Executes the full deterministic scoring engine pipeline.
        Calculates category scores, runs the provider-agnostic CandidateMatchingAgent,
        weights category scores reproducibly, and generates actionable recommendations.
        """
        pipeline_start = time.perf_counter()

        # 1. Skill Matching
        skill_score, matching_skills, missing_req, missing_pref = SkillMatcher.match_skills(resume, job)

        # 2. Experience Matching
        exp_score, exp_gap = ExperienceMatcher.match_experience(resume, job)

        # 3. Semantic Similarity Matching & Evidence Retrieval
        semantic_score, requirements_evidence = SemanticMatcher.match_semantic(resume, job)

        # 4. ATS & Keyword Analysis
        keyword_score, ats_analysis = ATSAnalyzer.analyze_ats(resume, job, raw_resume_text)

        # 5. Education Matching
        education_score = EducationMatcher.match_education(resume, job)

        # 6. Configurable Weighted Deterministic Score Calculation
        overall = (
            skill_score * settings.WEIGHT_SKILLS
            + exp_score * settings.WEIGHT_EXPERIENCE
            + semantic_score * settings.WEIGHT_SEMANTIC
            + keyword_score * settings.WEIGHT_KEYWORDS
            + education_score * settings.WEIGHT_EDUCATION
        )
        overall_score = round(max(0.0, min(100.0, overall)), 2)

        scoring_weights = {
            "skills": settings.WEIGHT_SKILLS,
            "experience": settings.WEIGHT_EXPERIENCE,
            "semantic": settings.WEIGHT_SEMANTIC,
            "keywords": settings.WEIGHT_KEYWORDS,
            "education": settings.WEIGHT_EDUCATION,
        }

        # 7. AI Matching & Evidence Verification Agent (provider-independent via BaseAIProvider)
        ai_assessment: Optional[CandidateMatchAssessment] = None
        ai_primary_failed = False
        try:
            ai_assessment, ai_primary_failed = run_with_ai_fallback(
                "assess_candidate_match",
                lambda provider: CandidateMatchingAgent(provider).evaluate(
                    candidate_id=candidate_id or resume.email or resume.name or "candidate",
                    resume=resume,
                    job=job,
                    relevant_evidence=requirements_evidence,
                ),
            )
        except Exception as exc:
            ai_primary_failed = True
            # Never crash deterministic matching when AI provider is unavailable or strict fallback is off
            logger.warning(f"Skipping AI matching assessment after provider error: {type(exc).__name__}")

        analysis_result = AnalysisResultData(
            overall_score=overall_score,
            skill_score=skill_score,
            experience_score=exp_score,
            education_score=education_score,
            keyword_score=keyword_score,
            semantic_score=semantic_score,
            matching_skills=matching_skills,
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
            experience_gap_analysis=exp_gap,
            ats_analysis=ats_analysis,
            requirements_evidence=requirements_evidence,
            scoring_weights=scoring_weights,
            ai_matching_assessment=ai_assessment,
        )

        # 8. Actionable Recommendations
        matching_context = {
            "overall_score": overall_score,
            "matching_skills": [s.model_dump() for s in matching_skills],
            "missing_required_skills": [s.model_dump() for s in missing_req],
            "missing_preferred_skills": [s.model_dump() for s in missing_pref],
            "experience_gap": exp_gap.model_dump(),
            "ats_score": ats_analysis.estimated_ats_score,
        }

        recommendations: List[RecommendationItem] = []
        try:
            # If the primary provider already timed out / failed in step 7, avoid waiting a second
            # full timeout sequentially by routing directly to configured fallback if available.
            from backend.app.ai import get_ai_provider, get_fallback_ai_provider

            primary_provider = get_ai_provider()
            preferred_provider = (
                get_fallback_ai_provider(primary_provider.provider_name)
                if ai_primary_failed
                else None
            )
            if ai_primary_failed and preferred_provider is None:
                logger.warning("Skipping recommendations after primary AI provider failure.")
            else:
                recommendations, _ = run_with_ai_fallback(
                    "generate_recommendations",
                    lambda provider: provider.generate_recommendations(resume, job, matching_context),
                    primary_provider=preferred_provider or primary_provider,
                )
        except Exception as exc:
            logger.warning(
                f"Recommendations generation skipped after provider failure: {type(exc).__name__}"
            )

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(f"ScoringEngine pipeline completed in {total_ms:.1f}ms overall_score={overall_score}")

        return analysis_result, recommendations
