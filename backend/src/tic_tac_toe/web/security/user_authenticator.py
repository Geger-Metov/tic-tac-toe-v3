from uuid import UUID

from fastapi import Header, HTTPException, status

from tic_tac_toe.domain.exception.auth_exceptions import InvalidTokenError
from tic_tac_toe.web.route.deps import AuthServiceDep

_BEARER_PREFIX = "Bearer "


async def get_current_user_id(
    auth_service: AuthServiceDep,
    authorization: str | None = Header(default=None),
) -> UUID:
    """
    UserAuthenticator: Basic-авторизация убрана, вместо неё — Bearer.
    Достаёт accessToken из "Authorization: Bearer {accessToken}", проверяет
    через JwtProvider (внутри AuthService) и отдаёт UUID пользователя.
    Любая проблема — 401, тело эндпоинта не выполняется.
    """
    if authorization is None or not authorization.startswith(_BEARER_PREFIX):
        raise _unauthorized("Missing or malformed Authorization header")

    token = authorization[len(_BEARER_PREFIX) :].strip()
    try:
        return await auth_service.get_user_id_from_access_token(token)
    except InvalidTokenError as e:
        raise _unauthorized("Invalid or expired token") from e


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
