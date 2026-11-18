from fastapi import APIRouter, HTTPException, status

from tic_tac_toe.domain.exception.auth_exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TooManyLoginAttemptsError,
    UserAlreadyExistsError,
)
from tic_tac_toe.web.model.request_model import (
    JwtRequest,
    RefreshJwtRequest,
    SignUpRequest,
)
from tic_tac_toe.web.model.response_model import (
    JwtResponse,
    SignUpResponse,
    UserResponse,
)
from tic_tac_toe.web.route.deps import AuthServiceDep, CurrentUserId, UserServiceDep

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request_data: SignUpRequest, service: AuthServiceDep) -> SignUpResponse:
    try:
        user = await service.register(request_data.login, request_data.password)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this login already exists",
        )
    return SignUpResponse(success=True, id=user.id)


@router.post("/login")
async def login(request_data: JwtRequest, service: AuthServiceDep) -> JwtResponse:
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
@router.post("/token/access")
async def refresh_access_token(
    request_data: RefreshJwtRequest,
    service: AuthServiceDep,
) -> JwtResponse:
    try:
        access, refresh = await service.refresh_access_token(request_data.refreshToken)
    except InvalidTokenError:
        raise _invalid_refresh()
    return JwtResponse(accessToken=access, refreshToken=refresh)


@router.post("/token/refresh")
async def refresh_refresh_token(
    request_data: RefreshJwtRequest,
    service: AuthServiceDep,
) -> JwtResponse:
    try:
        access, refresh = await service.refresh_refresh_token(request_data.refreshToken)
    except InvalidTokenError:
        raise _invalid_refresh()
    return JwtResponse(accessToken=access, refreshToken=refresh)


@router.get("/me")
async def me(user_id: CurrentUserId, service: UserServiceDep) -> UserResponse:
    """Информация о пользователе по accessToken."""
    user = await service.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=user.id, login=user.login)
