from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.job import JobListResponse
from backend.app.schemas.resume import ResumeListResponse


class ApplicationCreate(BaseModel):
    job_id: str
    resume_id: Optional[str] = None
    status: str = Field(default="Saved", description="Saved, Applied, Interview, Offer, Rejected")
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    resume_id: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: str
    user_id: str
    job_id: str
    resume_id: Optional[str] = None
    status: str
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    job: Optional[JobListResponse] = None
    resume: Optional[ResumeListResponse] = None

    model_config = ConfigDict(from_attributes=True)
