from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.job import Job, JobEmbedding
from backend.app.repositories.base_repository import BaseRepository


class JobRepository(BaseRepository[Job]):
    def __init__(self):
        super().__init__(Job)

    def get_user_jobs(self, db: Session, user_id: str, skip: int = 0, limit: int = 50) -> List[Job]:
        return (
            db.query(Job)
            .filter(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_id(self, db: Session, user_id: str, job_id: str) -> Optional[Job]:
        return db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()

    def add_embeddings(self, db: Session, embeddings: List[JobEmbedding]) -> None:
        db.add_all(embeddings)
        db.commit()

    def get_embeddings(self, db: Session, job_id: str) -> List[JobEmbedding]:
        return db.query(JobEmbedding).filter(JobEmbedding.job_id == job_id).all()


job_repository = JobRepository()

