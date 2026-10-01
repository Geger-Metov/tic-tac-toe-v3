from uuid import UUID
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.exception.auth_exceptions import InvalidCredentialsError
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.infrastructure.database.session import get_db_session


def get_auth_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> IAuthService:
    container = request.app.state.container
    return container.get_auth_service(session)


async def get_current_user_id(
    authorization: str | None = Header(default=None),
    auth_service: IAuthService = Depends(get_auth_service),
) -> UUID:
    """
    UserAuthenticator из ТЗ.

    - Валидирует login/password из заголовка Authorization (Basic base64(login:password)).
    - При успехе — не блокирует запрос и отдаёт UUID пользователя как результат Depends,
      его может забрать эндпоинт (например, чтобы узнать, кто делает ход).
    - При неудаче — поднимает 401, и FastAPI не вызовет тело эндпоинта вообще:
      зависимость подняла исключение раньше, чем начал выполняться route handler.

    Заодно это и есть реализация эндпоинта логина: "аутентифицируй по Basic Auth
    и верни UUID" — ровно то же самое поведение, которое нужно для защиты
    остальных эндпоинтов, поэтому /auth/login просто переиспользует эту зависимость
    напрямую (см. auth_route.py), а не дублирует логику.
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Basic"},
        )
    try:
        return await auth_service.authenticate(authorization)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
            headers={"WWW-Authenticate": "Basic"},
        )
