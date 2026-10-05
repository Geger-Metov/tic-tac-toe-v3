from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.exception.auth_exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TooManyLoginAttemptsError,
    UserAlreadyExistsError,
)
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.database.session import get_db_session
from tic_tac_toe.web.model.request_model import JwtRequest, RefreshJwtRequest, SignUpRequest
from tic_tac_toe.web.model.response_model import JwtResponse, SignUpResponse, UserResponse
from tic_tac_toe.web.security.user_authenticator import get_auth_service, get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_user_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> IUserService:
    return request.app.state.container.get_user_service(session)


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def signup(request_data: SignUpRequest, service: IAuthService = Depends(get_auth_service)):
    try:
        user = await service.register(request_data.login, request_data.password)
    except UserAlreadyExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this login already exists")
    return SignUpResponse(success=True, id=user.id)


@router.post("/login", response_model=JwtResponse)
async def login(request_data: JwtRequest, service: IAuthService = Depends(get_auth_service)):
    try:
        access, refresh = await service.authenticate(request_data.login, request_data.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TooManyLoginAttemptsError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts, try again later",
            headers={"Retry-After": str(e.retry_after_seconds)},
        )
    return JwtResponse(accessToken=access, refreshToken=refresh)


# Оба refresh-эндпоинта открыты (без Bearer): клиент приходит сюда именно
# потому, что accessToken уже протух.
@router.post("/token/access", response_model=JwtResponse)
async def refresh_access_token(request_data: RefreshJwtRequest, service: IAuthService = Depends(get_auth_service)):
    try:
        access, refresh = await service.refresh_access_token(request_data.refreshToken)
    except InvalidTokenError:
        raise _invalid_refresh()
    return JwtResponse(accessToken=access, refreshToken=refresh)


@router.post("/token/refresh", response_model=JwtResponse)
async def refresh_refresh_token(request_data: RefreshJwtRequest, service: IAuthService = Depends(get_auth_service)):
    try:
        access, refresh = await service.refresh_refresh_token(request_data.refreshToken)
    except InvalidTokenError:
        raise _invalid_refresh()
    return JwtResponse(accessToken=access, refreshToken=refresh)


@router.get("/me", response_model=UserResponse)
async def me(
    user_id: UUID = Depends(get_current_user_id),
    user_service: IUserService = Depends(_get_user_service),
):
    """Информация о пользователе по accessToken."""
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=user.id, login=user.login)
