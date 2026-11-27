from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    TailorResumeResponse,
    CoverLetterRequest,
    CoverLetterResponse,
)
from backend.app.services.analysis_service import analysis_service

router = APIRouter()


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def run_analysis(
    analysis_in: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run comprehensive matching engine between a resume and job description.
    Computes overall score, category breakdowns, ATS analysis, and actionable recommendations.
    """
    return analysis_service.create_analysis(
        db=db,
        user_id=current_user.id,
        resume_id=analysis_in.resume_id,
        job_id=analysis_in.job_id,
    )


@router.get("", response_model=List[AnalysisResponse])
def list_analyses(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List historical analysis reports for currently authenticated user."""
    return analysis_service.get_user_analyses(db, current_user.id, skip=skip, limit=limit)


@router.get("/{id}", response_model=AnalysisResponse)
def get_analysis(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full analysis details, scores, ATS breakdown, and recommendations."""
    return analysis_service.get_analysis_by_id(db, current_user.id, id)


@router.post("/{id}/tailor-resume", response_model=TailorResumeResponse)
def tailor_resume(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate tailored resume content targeting the job without hallucinating experience.
    """
    return analysis_service.tailor_resume(db, current_user.id, id)


@router.post("/{id}/cover-letter", response_model=CoverLetterResponse)
def generate_cover_letter(
    id: str,
    request: CoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate tailored cover letter aligning candidate experience with job posting.
    """
    return analysis_service.generate_cover_letter(db, current_user.id, id, request)

