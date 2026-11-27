from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

WorkModeType = Literal["Remote", "Hybrid", "On-site"]


class StructuredJob(BaseModel):
    job_title: str = ""
    company: str = ""
    location: str = ""
    work_mode: str = "Hybrid"
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    employment_type: Optional[str] = None
    notice_period: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    years_of_experience: Optional[float] = None
    education_requirements: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company: str = Field(default="Hiring Organization", min_length=1, max_length=255)
    location: Optional[str] = None
    work_mode: WorkModeType = "Hybrid"
    min_experience: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    max_experience: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    education_requirements: List[str] = Field(default_factory=list)
    employment_type: Optional[str] = None
    notice_period: Optional[str] = None
    location_required: bool = False
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    description: str = Field(..., min_length=10)
    structured_data: Optional[StructuredJob] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[WorkModeType] = None
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    education_requirements: Optional[List[str]] = None
    employment_type: Optional[str] = None
    notice_period: Optional[str] = None
    location_required: Optional[bool] = None
    description: Optional[str] = None
    structured_data: Optional[StructuredJob] = None


class JobResponse(BaseModel):
    id: str
    user_id: str
    title: str
    company: str
    location: Optional[str] = None
    work_mode: str = "Hybrid"
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    education_requirements: Optional[List[str]] = None
    employment_type: Optional[str] = None
    notice_period: Optional[str] = None
    location_required: bool = False
    description: str
    structured_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    work_mode: str = "Hybrid"
    min_experience: Optional[float] = None
    max_experience: Optional[float] = None
    required_skills: Optional[List[str]] = None
    employment_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
