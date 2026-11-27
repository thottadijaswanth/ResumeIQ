from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.analysis import Analysis
from backend.app.repositories.base_repository import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    def __init__(self):
        super().__init__(Analysis)

    def get_user_analyses(self, db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Analysis]:
        return (
            db.query(Analysis)
            .filter(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_id(self, db: Session, user_id: str, analysis_id: str) -> Optional[Analysis]:
        return db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user_id).first()

    def get_by_resume_and_job(
        self, db: Session, user_id: str, resume_id: str, job_id: str
    ) -> Optional[Analysis]:
        return (
            db.query(Analysis)
            .filter(
                Analysis.user_id == user_id,
                Analysis.resume_id == resume_id,
                Analysis.job_id == job_id,
            )
            .first()
        )

    def get_for_job(self, db: Session, user_id: str, job_id: str) -> List[Analysis]:
        return (
            db.query(Analysis)
            .filter(Analysis.user_id == user_id, Analysis.job_id == job_id)
            .order_by(Analysis.overall_score.desc(), Analysis.created_at.desc())
            .all()
        )


analysis_repository = AnalysisRepository()
