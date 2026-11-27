from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.ai import (
    AIConfigurationError,
    get_ai_health_status,
    set_ai_provider_mode,
)
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.analysis import AIHealthResponse, AIModeUpdateRequest

router = APIRouter()


@router.get("/health", response_model=AIHealthResponse)
def ai_health_check():
    """
    Report active AI provider, configured model, mode (local/cloud/mock),
    and connectivity health without exposing sensitive credentials.
    """
    return get_ai_health_status()


@router.post("/mode", response_model=AIHealthResponse)
def switch_ai_mode(
    request: AIModeUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Switch active AI provider mode ('auto', 'ollama', 'openai', 'mock') without leaking keys."""
    try:
        return set_ai_provider_mode(request.provider, persist_env=True)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
