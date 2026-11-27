from typing import List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.application import Application
from backend.app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from backend.app.repositories.application_repository import application_repository
from backend.app.repositories.job_repository import job_repository


class ApplicationService:
    @staticmethod
    def create_application(db: Session, user_id: str, app_in: ApplicationCreate) -> ApplicationResponse:
        job = job_repository.get_by_user_and_id(db, user_id, app_in.job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        db_app = Application(
            user_id=user_id,
            job_id=app_in.job_id,
            resume_id=app_in.resume_id,
            status=app_in.status or "Saved",
            notes=app_in.notes,
            applied_at=app_in.applied_at or (datetime.utcnow() if app_in.status == "Applied" else None),
        )
        created = application_repository.create(db, db_app)
        return ApplicationResponse.model_validate(created)

    @staticmethod
    def get_user_applications(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[ApplicationResponse]:
        apps = application_repository.get_user_applications(db, user_id, skip=skip, limit=limit)
        return [ApplicationResponse.model_validate(a) for a in apps]

    @staticmethod
    def update_application(
        db: Session,
        user_id: str,
        application_id: str,
        app_update: ApplicationUpdate,
    ) -> ApplicationResponse:
        app = application_repository.get_by_user_and_id(db, user_id, application_id)
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        if app_update.status:
            app.status = app_update.status
            if app_update.status == "Applied" and not app.applied_at:
                app.applied_at = datetime.utcnow()
        if app_update.notes is not None:
            app.notes = app_update.notes
        if app_update.applied_at is not None:
            app.applied_at = app_update.applied_at
        if app_update.resume_id is not None:
            app.resume_id = app_update.resume_id

        updated = application_repository.update(db, app)
        return ApplicationResponse.model_validate(updated)

    @staticmethod
    def delete_application(db: Session, user_id: str, application_id: str) -> bool:
        app = application_repository.get_by_user_and_id(db, user_id, application_id)
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        return application_repository.delete(db, application_id)

    @staticmethod
    def get_dashboard_stats(db: Session, user_id: str) -> Dict[str, Any]:
        status_counts = application_repository.get_status_counts(db, user_id)
        total_apps = sum(status_counts.values())
        return {
            "total_applications": total_apps,
            "status_breakdown": status_counts,
        }


application_service = ApplicationService()

