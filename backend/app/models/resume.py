from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class Resume(BaseModel):
    __tablename__ = "resumes"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)  # pdf, docx
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)
    raw_text = Column(Text, nullable=False)
    structured_data = Column(JSON, nullable=True)
    candidate_years = Column(Float, nullable=True)
    candidate_location = Column(String(255), nullable=True)
    combined_embedding = Column(JSON, nullable=True)
    processing_status = Column(String(32), nullable=False, default="ready")  # pending, processing, ready, failed
    processing_error = Column(Text, nullable=True)
    ai_provider_used = Column(String(32), nullable=True)
    ai_model_used = Column(String(128), nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="resumes")
    embeddings = relationship("ResumeEmbedding", back_populates="resume", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="resume", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="resume")


class ResumeEmbedding(BaseModel):
    __tablename__ = "resume_embeddings"

    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_type = Column(String(64), nullable=False)  # summary, experience, project, skills
    chunk_text = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # Vector stored as JSON float array for max portability
    embedding_metadata = Column(JSON, nullable=True)

    # Relationships
    resume = relationship("Resume", back_populates="embeddings")
