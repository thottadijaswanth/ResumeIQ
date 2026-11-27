from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.resume import (
    BulkResumeUploadResponse,
    ResumeListResponse,
    ResumeResponse,
    ResumeUpdate,
)
from backend.app.services.resume_service import resume_service

router = APIRouter()


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def upload_resume(
    name: str = Form(""),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a single resume file (PDF or DOCX).
    Uses SHA-256 fingerprint caching to reuse previously extracted profiles and embeddings.
    """
    return resume_service.process_and_create_resume(
        db=db,
        user_id=current_user.id,
        name=name,
        file=file,
    )


@router.post("/batch", response_model=BulkResumeUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_resumes_batch(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload multiple resume files (PDF / DOCX) in one operation.
    Reuses cached profiles for duplicate files and isolates corrupt files without failing the batch.
    """
    files_payload = [
        (f.filename or "resume.pdf", f.file.read(), f.content_type or "")
        for f in files
    ]
    return resume_service.process_batch_resumes(
        db=db,
        user_id=current_user.id,
        files_payload=files_payload,
    )


@router.get("", response_model=List[ResumeListResponse])
def list_resumes(
    skip: int = 0,
    limit: int = 200,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List resumes uploaded by currently authenticated user."""
    return resume_service.get_user_resumes(db, current_user.id, skip=skip, limit=limit)


@router.get("/{id}", response_model=ResumeResponse)
def get_resume(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full structured resume data by ID."""
    return resume_service.get_resume_by_id(db, current_user.id, id)


@router.patch("/{id}", response_model=ResumeResponse)
def update_resume(
    id: str,
    update_data: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update resume metadata or structured information."""
    return resume_service.update_resume(db, current_user.id, id, update_data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a resume by ID."""
    resume_service.delete_resume(db, current_user.id, id)
    return None
