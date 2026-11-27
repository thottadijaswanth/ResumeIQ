from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.schemas.auth import RegisterRequest, LoginRequest, Token
from backend.app.services.auth_service import auth_service

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account and return access token."""
    return auth_service.register(db, request)


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user credentials and return access token."""
    return auth_service.login(db, request)

