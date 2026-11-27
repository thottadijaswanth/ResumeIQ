from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class ScreeningRun(BaseModel):
    __tablename__ = "screening_runs"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(32), nullable=False, default="queued")  # queued, processing, completed, completed_with_errors, failed
    stage = Column(String(32), nullable=False, default="queued")  # queued, filtering, embedding, reranking, scoring, done

    total_resumes = Column(Integer, nullable=False, default=0)
    processed_resumes = Column(Integer, nullable=False, default=0)
    matched_resumes = Column(Integer, nullable=False, default=0)
    failed_resumes = Column(Integer, nullable=False, default=0)
    shortlisted_count = Column(Integer, nullable=False, default=0)
    reranked_count = Column(Integer, nullable=False, default=0)

    ai_provider = Column(String(32), nullable=True)
    ai_model = Column(String(128), nullable=True)
    ai_rerank_used = Column(Boolean, nullable=False, default=False)
    ai_error = Column(Text, nullable=True)

    failed_files = Column(JSON, nullable=True)  # List of {filename, reason, resume_id?}
    resume_ids = Column(JSON, nullable=True)  # Selected resume IDs for this run
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    job = relationship("Job", back_populates="screening_runs")
    analyses = relationship("Analysis", back_populates="screening_run")

