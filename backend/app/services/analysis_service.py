from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.analysis import Analysis
from backend.app.schemas.analysis import (
    AnalysisResponse,
    TailorResumeResponse,
    CoverLetterResponse,
    CoverLetterRequest,
)
from backend.app.schemas.resume import StructuredResume
from backend.app.schemas.job import StructuredJob
from backend.app.repositories.resume_repository import resume_repository
from backend.app.repositories.job_repository import job_repository
from backend.app.repositories.analysis_repository import analysis_repository
from backend.app.matching.scoring_engine import ScoringEngine
from backend.app.ai import AIProviderError, run_with_ai_fallback
from backend.app.utils.logger import logger


class AnalysisService:
    @staticmethod
    def create_analysis(
        db: Session,
        user_id: str,
        resume_id: str,
        job_id: str,
    ) -> AnalysisResponse:
        resume = resume_repository.get_by_user_and_id(db, user_id, resume_id)
        if not resume:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

        job = job_repository.get_by_user_and_id(db, user_id, job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

        # Parse structured objects
        structured_resume = StructuredResume.model_validate(resume.structured_data)
        structured_job = StructuredJob.model_validate(job.structured_data)

        # Run deterministic scoring engine + AI matching agent
        analysis_result, recommendations = ScoringEngine.analyze_resume_against_job(
            resume=structured_resume,
            job=structured_job,
            raw_resume_text=resume.raw_text,
            candidate_id=resume.id,
        )

        # Save to database
        db_analysis = Analysis(
            user_id=user_id,
            resume_id=resume.id,
            job_id=job.id,
            overall_score=analysis_result.overall_score,
            skill_score=analysis_result.skill_score,
            experience_score=analysis_result.experience_score,
            education_score=analysis_result.education_score,
            keyword_score=analysis_result.keyword_score,
            semantic_score=analysis_result.semantic_score,
            analysis_result=analysis_result.model_dump(),
            recommendations=[r.model_dump() for r in recommendations],
        )
        created = analysis_repository.create(db, db_analysis)
        return AnalysisResponse.model_validate(created)

    @staticmethod
    def get_user_analyses(db: Session, user_id: str, skip: int = 0, limit: int = 50) -> List[AnalysisResponse]:
        analyses = analysis_repository.get_user_analyses(db, user_id, skip=skip, limit=limit)
        return [AnalysisResponse.model_validate(a) for a in analyses]

    @staticmethod
    def get_analysis_by_id(db: Session, user_id: str, analysis_id: str) -> AnalysisResponse:
        analysis = analysis_repository.get_by_user_and_id(db, user_id, analysis_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis report not found")
        return AnalysisResponse.model_validate(analysis)

    @staticmethod
    def tailor_resume(db: Session, user_id: str, analysis_id: str) -> TailorResumeResponse:
        analysis = analysis_repository.get_by_user_and_id(db, user_id, analysis_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis report not found")

        resume = resume_repository.get_by_user_and_id(db, user_id, analysis.resume_id)
        job = job_repository.get_by_user_and_id(db, user_id, analysis.job_id)

        structured_resume = StructuredResume.model_validate(resume.structured_data)
        structured_job = StructuredJob.model_validate(job.structured_data)

        try:
            result, _ = run_with_ai_fallback(
                "tailor_resume",
                lambda provider: provider.tailor_resume(
                    structured_resume,
                    structured_job,
                    analysis.analysis_result,
                ),
            )
            return result
        except AIProviderError as exc:
            logger.error(f"Tailor resume AI error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI tailoring service unavailable: {exc}",
            )
        except Exception as exc:
            logger.error(f"Tailor resume failed: {type(exc).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to tailor resume with the configured AI provider.",
            )

    @staticmethod
    def generate_cover_letter(
        db: Session,
        user_id: str,
        analysis_id: str,
        request: CoverLetterRequest,
    ) -> CoverLetterResponse:
        analysis = analysis_repository.get_by_user_and_id(db, user_id, analysis_id)
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis report not found")

        resume = resume_repository.get_by_user_and_id(db, user_id, analysis.resume_id)
        job = job_repository.get_by_user_and_id(db, user_id, analysis.job_id)

        structured_resume = StructuredResume.model_validate(resume.structured_data)
        structured_job = StructuredJob.model_validate(job.structured_data)

        try:
            result, _ = run_with_ai_fallback(
                "generate_cover_letter",
                lambda provider: provider.generate_cover_letter(
                    structured_resume,
                    structured_job,
                    tone=request.tone or "Professional",
                    custom_notes=request.custom_notes,
                ),
            )
            return result
        except AIProviderError as exc:
            logger.error(f"Cover letter AI error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI cover letter service unavailable: {exc}",
            )
        except Exception as exc:
            logger.error(f"Cover letter generation failed: {type(exc).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to generate cover letter with the configured AI provider.",
            )


analysis_service = AnalysisService()

