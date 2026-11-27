from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.application import Application
from backend.app.repositories.base_repository import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self):
        super().__init__(Application)

    def get_user_applications(self, db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Application]:
        return (
            db.query(Application)
            .filter(Application.user_id == user_id)
            .order_by(Application.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_id(self, db: Session, user_id: str, application_id: str) -> Optional[Application]:
        return (
            db.query(Application)
            .filter(Application.id == application_id, Application.user_id == user_id)
            .first()
        )

    def get_status_counts(self, db: Session, user_id: str) -> Dict[str, int]:
        results = (
            db.query(Application.status, func.count(Application.id))
            .filter(Application.user_id == user_id)
            .group_by(Application.status)
            .all()
        )
        counts = {
            "Saved": 0,
            "Applied": 0,
            "Interview": 0,
            "Offer": 0,
            "Rejected": 0,
        }
        for status, count in results:
            counts[status] = count
        return counts


application_repository = ApplicationRepository()

