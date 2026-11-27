from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.schemas.auth import RegisterRequest, LoginRequest, Token
from backend.app.schemas.user import UserResponse
from backend.app.repositories.user_repository import user_repository
from backend.app.utils.security import hash_password, verify_password, create_access_token


class AuthService:
    @staticmethod
    def register(db: Session, request: RegisterRequest) -> Token:
        normalized_email = request.email.lower().strip()
        existing_user = user_repository.get_by_email(db, normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        new_user = User(
            email=normalized_email,
            password_hash=hash_password(request.password),
            full_name=request.full_name.strip(),
            is_active=True,
        )
        user = user_repository.create(db, new_user)
        access_token = create_access_token(user.id)

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def login(db: Session, request: LoginRequest) -> Token:
        normalized_email = request.email.lower().strip()
        user = user_repository.get_by_email(db, normalized_email)
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is inactive.",
            )

        access_token = create_access_token(user.id)
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )


auth_service = AuthService()

