from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.database.session import get_db_session
from tic_tac_toe.web.model.response_model import UserResponse
from tic_tac_toe.web.security.user_authenticator import get_current_user_id

router = APIRouter(
    prefix="/users", 
    tags=["users"],
    dependencies=[Depends(get_current_user_id)],
)


def get_user_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> IUserService:
    container = request.app.state.container
    return container.get_user_service(session)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: IUserService = Depends(get_user_service),
):
    user = await service.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(id=user.id, login=user.login)
