from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.database.session import DbSession
from tic_tac_toe.web.model.response_model import UserResponse
from tic_tac_toe.web.security.user_authenticator import get_current_user_id

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user_id)],
)


def get_user_service(
    request: Request,
    session: DbSession,
) -> IUserService:
    container = request.app.state.container
    return container.get_user_service(session)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: IUserService = Depends(get_user_service),
    # UserAuthenticator: сам факт запроса требует авторизации (ТЗ — "require
    # authorization for all other endpoints"), но кого именно смотреть — решает
    # user_id из пути, не текущий пользователь.
    _current_user_id: UUID = Depends(get_current_user_id),
):
    user = await service.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=user.id, login=user.login)
