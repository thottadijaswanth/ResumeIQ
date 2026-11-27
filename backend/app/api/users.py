from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserResponse, UserUpdate
from backend.app.repositories.user_repository import user_repository

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get profile of currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile information of currently authenticated user."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name.strip()
    if user_update.email is not None:
        current_user.email = user_update.email.lower().strip()

    updated = user_repository.update(db, current_user)
    return updated

