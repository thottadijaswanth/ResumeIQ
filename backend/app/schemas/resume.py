from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExperienceItem(BaseModel):
    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    duration: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: Optional[str] = None


class ProjectItem(BaseModel):
    name: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)


class StructuredResume(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)


class ResumeCreate(BaseModel):
    name: str
    original_filename: str
    file_type: str
    file_size: int
    raw_text: str
    structured_data: Optional[StructuredResume] = None


class ResumeUpdate(BaseModel):
    name: Optional[str] = None
    structured_data: Optional[StructuredResume] = None


class ResumeResponse(BaseModel):
    id: str
    user_id: str
    name: str
    original_filename: str
    file_type: str
    file_size: int
    file_hash: Optional[str] = None
    raw_text: str
    structured_data: Optional[Dict[str, Any]] = None
    candidate_years: Optional[float] = None
    candidate_location: Optional[str] = None
    processing_status: str = "ready"
    processing_error: Optional[str] = None
    ai_provider_used: Optional[str] = None
    ai_model_used: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeListResponse(BaseModel):
    id: str
    name: str
    original_filename: str
    file_type: str
    file_size: int
    file_hash: Optional[str] = None
    candidate_years: Optional[float] = None
    candidate_location: Optional[str] = None
    processing_status: str = "ready"
    skills: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkResumeFailureItem(BaseModel):
    filename: str
    reason: str


class BulkResumeUploadItem(BaseModel):
    id: str
    name: str
    original_filename: str
    cached: bool = False
    candidate_years: Optional[float] = None
    candidate_location: Optional[str] = None
    skills_count: int = 0


class BulkResumeUploadResponse(BaseModel):
    total_received: int
    processed_count: int
    cached_count: int
    failed_count: int
    resumes: List[BulkResumeUploadItem] = Field(default_factory=list)
    failed_files: List[BulkResumeFailureItem] = Field(default_factory=list)
