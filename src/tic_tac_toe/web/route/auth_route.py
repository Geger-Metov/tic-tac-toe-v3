from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from tic_tac_toe.domain.exception.auth_exceptions import UserAlreadyExistsError
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.web.model.request_model import SignUpRequest
from tic_tac_toe.web.model.response_model import LoginResponse, SignUpResponse
from tic_tac_toe.web.security.user_authenticator import get_auth_service, get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request_data: SignUpRequest,
    service: IAuthService = Depends(get_auth_service),
):
    """Открытый эндпоинт — UserAuthenticator сюда не применяется."""
    try:
        user = await service.register(request_data.login, request_data.password)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this login already exists",
        )
    return SignUpResponse(success=True, id=user.id)


@router.post("/login", response_model=LoginResponse)
async def login(user_id: UUID = Depends(get_current_user_id)):
    """
    Открытый эндпоинт с точки зрения "не требует предварительной авторизации",
    но по сути ЕСТЬ сама проверка авторизации: get_current_user_id (UserAuthenticator)
    читает Basic-заголовок, проверяет логин/пароль и либо возвращает UUID,
    либо поднимает 401 ещё до того, как тело этой функции начнёт выполняться.
    """
    return LoginResponse(user_id=user_id)
