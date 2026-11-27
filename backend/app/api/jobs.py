from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.analysis import (
    CandidateDetailResponse,
    CandidateRankItem,
    ScreeningRunRequest,
    ScreeningRunResponse,
)
from backend.app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobResponse,
    JobUpdate,
)
from backend.app.schemas.resume import BulkResumeUploadResponse
from backend.app.services.job_service import job_service
from backend.app.services.resume_service import resume_service
from backend.app.services.screening_service import screening_service

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_in: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a structured job posting (role, location, work mode, experience range,
    required/preferred skills, description) and generate cached embeddings.
    """
    return job_service.create_job(db=db, user_id=current_user.id, job_in=job_in)


@router.get("", response_model=List[JobListResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all job postings created by currently authenticated user."""
    return job_service.get_user_jobs(db, current_user.id, skip=skip, limit=limit)


@router.get("/{id}", response_model=JobResponse)
def get_job(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full structured job requirements and details by ID."""
    return job_service.get_job_by_id(db, current_user.id, id)


@router.patch("/{id}", response_model=JobResponse)
def update_job(
    id: str,
    update_data: JobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update job posting details or requirements."""
    return job_service.update_job(db, current_user.id, id, update_data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a job posting by ID."""
    job_service.delete_job(db, current_user.id, id)
    return None


@router.post(
    "/{id}/resumes",
    response_model=BulkResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_resumes_for_job(
    id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload multiple candidate resumes (PDF/DOCX) for a job opening.
    Candidates are stored once in the reusable repository with SHA-256 caching.
    """
    job_service.get_job_by_id(db, current_user.id, id)
    files_payload = [
        (f.filename or "resume.pdf", f.file.read(), f.content_type or "")
        for f in files
    ]
    return resume_service.process_batch_resumes(
        db=db,
        user_id=current_user.id,
        files_payload=files_payload,
    )


@router.post(
    "/{id}/screen",
    response_model=ScreeningRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def screen_candidates_for_job(
    id: str,
    request: ScreeningRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Launch asynchronous multi-stage candidate screening against this job:
    hard filters + cached embeddings -> top-K shortlist -> concise AI reranking -> final score.
    """
    run = screening_service.create_screening_run(db, current_user.id, id, request)
    background_tasks.add_task(
        screening_service.run_screening_pipeline,
        run.id,
        use_ai_rerank=request.use_ai_rerank,
        rerank_top_k=request.rerank_top_k,
    )
    return ScreeningRunResponse.model_validate(run)


@router.get("/{id}/screening-status", response_model=ScreeningRunResponse)
def get_job_screening_status(
    id: str,
    run_id: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll progressive screening status and live top candidates."""
    return screening_service.get_screening_status(db, current_user.id, id, run_id=run_id)


@router.get("/{id}/candidates", response_model=List[CandidateRankItem])
def list_job_candidates(
    id: str,
    min_score: Optional[float] = Query(default=None, ge=0.0, le=100.0),
    min_experience: Optional[float] = Query(default=None, ge=0.0),
    location: Optional[str] = Query(default=None),
    required_skill: Optional[str] = Query(default=None),
    classification: Optional[str] = Query(default=None),
    sort_by: str = Query(default="score_desc"),
    limit: int = Query(default=200, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List ranked, filterable, sortable candidate matches for a single job."""
    return screening_service.get_ranked_candidates(
        db,
        current_user.id,
        id,
        min_score=min_score,
        min_experience=min_experience,
        location=location,
        required_skill=required_skill,
        classification=classification,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/{id}/candidates/{candidate_id}", response_model=CandidateDetailResponse)
def get_job_candidate_detail(
    id: str,
    candidate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inspect detailed match evidence, gaps, and structured profile for one candidate."""
    return screening_service.get_candidate_detail(db, current_user.id, id, candidate_id)
