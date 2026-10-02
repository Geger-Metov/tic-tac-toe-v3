from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from tic_tac_toe.domain.exception.auth_exceptions import InvalidTokenError
from tic_tac_toe.domain.model.user import User
from tic_tac_toe.domain.service.jwt_interface import IJwtProvider

_ALGORITHM = "HS256"
_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


class JwtProvider(IJwtProvider):
    def __init__(self, secret_key: str, access_expires: timedelta, refresh_expires: timedelta) -> None:
        self._secret_key = secret_key
        self._access_expires = access_expires
        self._refresh_expires = refresh_expires

    def generate_access_token(self, user: User) -> str:
        return self._generate(user, self._access_expires, _ACCESS_TYPE)

    def generate_refresh_token(self, user: User) -> str:
        return self._generate(user, self._refresh_expires, _REFRESH_TYPE)

    def validate_access_token(self, token: str) -> bool:
        return self._validate(token, _ACCESS_TYPE)

    def validate_refresh_token(self, token: str) -> bool:
        return self._validate(token, _REFRESH_TYPE)

    def get_user_id(self, token: str) -> UUID:
        payload = self._decode(token)
        try:
            return UUID(payload["sub"])
        except (KeyError, ValueError):
            raise InvalidTokenError("token has no valid 'sub' claim")

    def get_jti(self, token: str) -> str:
        payload = self._decode(token)
        try:
            return payload["jti"]
        except KeyError:
            raise InvalidTokenError("token has no 'jti' claim")

    def _generate(self, user: User, expires_delta: timedelta, token_type: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),   # UUID пользователя — то, что просит ТЗ "saving the UUID in the token"
            "type": token_type,    # отличает access от refresh — без этого одним и тем же
                                    # токеном можно было бы пройти оба validate_*_token
            "iat": now,
            "exp": now + expires_delta,
            "jti": str(uuid4()),  # уникальный id токена — нужен для отслеживания
                                        # одноразовости refreshToken на уровне AuthService
        }
        return jwt.encode(payload, self._secret_key, algorithm=_ALGORITHM)

    def _decode(self, token: str) -> dict:
        try:
            return jwt.decode(token, self._secret_key, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as e:
            raise InvalidTokenError(str(e)) from e

    def _validate(self, token: str, expected_type: str) -> bool:
        try:
            payload = self._decode(token)
        except InvalidTokenError:
            return False
        return payload.get("type") == expected_type
