from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class RefreshTokenRecord:
    jti: UUID
    user_id: UUID
    used: bool
    expires_at: datetime
