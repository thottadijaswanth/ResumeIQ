from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Analysis(BaseModel):
    __tablename__ = "analyses"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    screening_run_id = Column(
        String(36), ForeignKey("screening_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    overall_score = Column(Float, nullable=False)
    skill_score = Column(Float, nullable=False)
    experience_score = Column(Float, nullable=False)
    education_score = Column(Float, nullable=False)
    keyword_score = Column(Float, nullable=False)
    semantic_score = Column(Float, nullable=False)

    match_classification = Column(String(32), nullable=True)  # STRONG_MATCH, GOOD_MATCH, PARTIAL_MATCH, WEAK_MATCH
    ai_reranked = Column(Boolean, nullable=False, default=False)
    hard_filter_passed = Column(Boolean, nullable=False, default=True)
    hard_filter_notes = Column(JSON, nullable=True)
    rank_position = Column(Integer, nullable=True)

    analysis_result = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)

    # Relationships
    user = relationship("User", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    job = relationship("Job", back_populates="analyses")
    screening_run = relationship("ScreeningRun", back_populates="analyses")
