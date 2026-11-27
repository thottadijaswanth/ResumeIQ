from sqlalchemy import Boolean, Column, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Job(BaseModel):
    __tablename__ = "jobs"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    work_mode = Column(String(32), nullable=False, default="Hybrid")  # Remote, Hybrid, On-site
    min_experience = Column(Float, nullable=True)
    max_experience = Column(Float, nullable=True)
    required_skills = Column(JSON, nullable=True)
    preferred_skills = Column(JSON, nullable=True)
    education_requirements = Column(JSON, nullable=True)
    employment_type = Column(String(64), nullable=True)
    notice_period = Column(String(64), nullable=True)
    location_required = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=False)
    structured_data = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")
    embeddings = relationship("JobEmbedding", back_populates="job", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    screening_runs = relationship("ScreeningRun", back_populates="job", cascade="all, delete-orphan")


class JobEmbedding(BaseModel):
    __tablename__ = "job_embeddings"

    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_type = Column(String(64), nullable=False)  # responsibility, requirement, skill, qualification, combined
    chunk_text = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # Vector stored as JSON float array for max portability
    embedding_metadata = Column(JSON, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="embeddings")
