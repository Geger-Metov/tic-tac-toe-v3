from tic_tac_toe.domain.model.refresh_token import RefreshTokenRecord as DomainRefreshToken
from tic_tac_toe.infrastructure.persistence.model.refresh_token_model import RefreshTokenModel


def to_data(domain: DomainRefreshToken) -> RefreshTokenModel:
    return RefreshTokenModel(
        jti=domain.jti,
        user_id=domain.user_id,
        used=domain.used,
        expires_at=domain.expires_at,
    )


def to_domain(data: RefreshTokenModel) -> DomainRefreshToken:
    return DomainRefreshToken(
        jti=data.jti,
        user_id=data.user_id,
        used=data.used,
        expires_at=data.expires_at,
    )
