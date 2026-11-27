from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.resume import Resume, ResumeEmbedding
from backend.app.repositories.base_repository import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self):
        super().__init__(Resume)

    def get_user_resumes(self, db: Session, user_id: str, skip: int = 0, limit: int = 200) -> List[Resume]:
        return (
            db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_id(self, db: Session, user_id: str, resume_id: str) -> Optional[Resume]:
        return db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()

    def get_by_user_and_hash(self, db: Session, user_id: str, file_hash: str) -> Optional[Resume]:
        return (
            db.query(Resume)
            .filter(
                Resume.user_id == user_id,
                Resume.file_hash == file_hash,
                Resume.processing_status == "ready",
                Resume.ai_model_used == "fast-extractor-v2",
            )
            .first()
        )

    def get_ready_resumes(
        self, db: Session, user_id: str, resume_ids: Optional[List[str]] = None
    ) -> List[Resume]:
        query = db.query(Resume).filter(
            Resume.user_id == user_id, Resume.processing_status == "ready"
        )
        if resume_ids is not None:
            if not resume_ids:
                return []
            query = query.filter(Resume.id.in_(resume_ids))
        return query.order_by(Resume.created_at.desc()).all()

    def add_embeddings(self, db: Session, embeddings: List[ResumeEmbedding]) -> None:
        db.add_all(embeddings)
        db.commit()

    def get_embeddings(self, db: Session, resume_id: str) -> List[ResumeEmbedding]:
        return db.query(ResumeEmbedding).filter(ResumeEmbedding.resume_id == resume_id).all()


resume_repository = ResumeRepository()
