from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from tic_tac_toe.web.model.response_model import UserResponse
from tic_tac_toe.web.route.deps import UserServiceDep
from tic_tac_toe.web.security.user_authenticator import get_current_user_id

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user_id)],
)


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    service: UserServiceDep,
    # UserAuthenticator: сам факт запроса требует авторизации (ТЗ — "require
    # authorization for all other endpoints"), но кого именно смотреть — решает
    # user_id из пути, не текущий пользователь.
) -> UserResponse:
    user = await service.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=user.id, login=user.login)
