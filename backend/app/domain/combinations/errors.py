from __future__ import annotations

from app.domain.errors import ValidationError


class InvalidCombinationStatusError(ValidationError):
    def __init__(self, status: str) -> None:
        super().__init__(f"{status!r} is not a valid combination status")
        self.status = status
