from uuid import UUID
from datetime import datetime
from sqlalchemy import Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from tic_tac_toe.infrastructure.database.base import Base


class RefreshTokenModel(Base):
    """
    Не сам JWT (его мы не храним — он самодостаточен и проверяется подписью),
    а факт "этот конкретный refreshToken (по его jti) был выпущен и ещё не
    использован". Без этой таблицы у сервера нет способа отследить, что
    refreshToken должен быть одноразовым — сам JWT остаётся валидным по
    подписи и сроку действия сколько угодно раз, пока не истечёт.
    """
    __tablename__ = "refresh_tokens"

    # jti — PK: он уже уникален по построению (uuid4 в JwtProvider), и он же
    # то единственное, по чему нам нужно искать запись.
    jti: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
