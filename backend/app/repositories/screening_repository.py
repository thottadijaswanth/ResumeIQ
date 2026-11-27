from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.screening import ScreeningRun
from backend.app.repositories.base_repository import BaseRepository


class ScreeningRepository(BaseRepository[ScreeningRun]):
    def __init__(self):
        super().__init__(ScreeningRun)

    def get_by_user_and_id(
        self, db: Session, user_id: str, run_id: str
    ) -> Optional[ScreeningRun]:
        return (
            db.query(ScreeningRun)
            .filter(ScreeningRun.id == run_id, ScreeningRun.user_id == user_id)
            .first()
        )

    def get_latest_for_job(
        self, db: Session, user_id: str, job_id: str
    ) -> Optional[ScreeningRun]:
        return (
            db.query(ScreeningRun)
            .filter(ScreeningRun.user_id == user_id, ScreeningRun.job_id == job_id)
            .order_by(ScreeningRun.created_at.desc())
            .first()
        )

    def list_for_job(
        self, db: Session, user_id: str, job_id: str, limit: int = 20
    ) -> List[ScreeningRun]:
        return (
            db.query(ScreeningRun)
            .filter(ScreeningRun.user_id == user_id, ScreeningRun.job_id == job_id)
            .order_by(ScreeningRun.created_at.desc())
            .limit(limit)
            .all()
        )


screening_repository = ScreeningRepository()

