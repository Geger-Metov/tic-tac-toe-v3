from datetime import datetime, timedelta, timezone
from typing import Tuple
from uuid import UUID

from tic_tac_toe.datasource.repository.refresh_token_repository import RefreshTokenRepo
from tic_tac_toe.domain.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from tic_tac_toe.domain.model.refresh_token import RefreshTokenRecord
from tic_tac_toe.domain.model.user import User
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.jwt_interface import IJwtProvider
from tic_tac_toe.domain.service.user_interface import IUserService


class AuthService(IAuthService):
    def __init__(
        self,
        user_service: IUserService,
        jwt_provider: IJwtProvider,
        refresh_token_repo: RefreshTokenRepo,
        refresh_expires: timedelta,
    ) -> None:
        self._user_service = user_service
        self._jwt_provider = jwt_provider
        self._refresh_token_repo = refresh_token_repo
        self._refresh_expires = refresh_expires

    async def register(self, login: str, password: str) -> User:
        return await self._user_service.register(login, password)

    async def authenticate(self, login: str, password: str) -> Tuple[str, str]:
        user = await self._user_service.get_by_login(login)
        if user is None or not self._user_service.verify_password(user, password):
            raise InvalidCredentialsError()
        return await self._issue_token_pair(user)

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        return await self._rotate(refresh_token)

    async def refresh_refresh_token(self, refresh_token: str) -> Tuple[str, str]:
        return await self._rotate(refresh_token)

    async def get_user_id_from_access_token(self, access_token: str) -> UUID:
        if not self._jwt_provider.validate_access_token(access_token):
            raise InvalidTokenError("invalid access token")
        return self._jwt_provider.get_user_id(access_token)

    # ---- внутреннее ----------------------------------------------------

    async def _rotate(self, refresh_token: str) -> Tuple[str, str]:
        """
        Проверяет подпись/срок/тип, затем что refreshToken ещё не использован
        (по записи в refresh_tokens), помечает его использованным и выдаёт
        новую пару. Все причины отказа сводятся к одному InvalidTokenError.
        """
        if not self._jwt_provider.validate_refresh_token(refresh_token):
            raise InvalidTokenError("invalid refresh token")

        try:
            jti = UUID(self._jwt_provider.get_jti(refresh_token))
        except ValueError:
            raise InvalidTokenError("invalid refresh token")

        record = await self._refresh_token_repo.find_by_jti(jti)
        if record is None:
            raise InvalidTokenError("invalid refresh token")

        # Единственная проверка "ещё не использован" — атомарный захват в БД
        # (см. RefreshTokenRepo.mark_used_if_unused). Нельзя заменить на
        # "прочитал record.used, потом записал": при двух параллельных
        # запросах оба прошли бы проверку. Повторное использование и проигрыш
        # гонки клиенту неотличимы от остальных причин отказа.
        if not await self._refresh_token_repo.mark_used_if_unused(jti):
            raise InvalidTokenError("invalid refresh token")

        user = await self._user_service.get_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("invalid refresh token")

        return await self._issue_token_pair(user)

    async def _issue_token_pair(self, user: User) -> Tuple[str, str]:
        access_token = self._jwt_provider.generate_access_token(user)
        refresh_token = self._jwt_provider.generate_refresh_token(user)

        jti = UUID(self._jwt_provider.get_jti(refresh_token))
        await self._refresh_token_repo.save(
            RefreshTokenRecord(
                jti=jti,
                user_id=user.id,
                used=False,
                expires_at=datetime.now(timezone.utc) + self._refresh_expires,
            )
        )
        return access_token, refresh_token
