from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from backend.app.services.application_service import application_service

router = APIRouter()


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    app_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new job application tracking card."""
    return application_service.create_application(db, current_user.id, app_in)


@router.get("", response_model=List[ApplicationResponse])
def list_applications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List tracked applications for currently authenticated user."""
    return application_service.get_user_applications(db, current_user.id, skip=skip, limit=limit)


@router.patch("/{id}", response_model=ApplicationResponse)
def update_application(
    id: str,
    app_update: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update application tracking status (Saved, Applied, Interview, Offer, Rejected) or notes."""
    return application_service.update_application(db, current_user.id, id, app_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an application entry."""
    application_service.delete_application(db, current_user.id, id)
    return None


@router.get("/stats/summary", response_model=Dict[str, Any])
def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get aggregate application metrics by status."""
    return application_service.get_dashboard_stats(db, current_user.id)

