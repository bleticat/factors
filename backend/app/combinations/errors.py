from __future__ import annotations

from app.shared.errors import NotFoundError, ValidationError


class CombinationNotFoundError(NotFoundError):
    def __init__(self, combination_id: int) -> None:
        super().__init__(f"Combination {combination_id} not found")
        self.combination_id = combination_id


class InvalidCombinationStatusError(ValidationError):
    def __init__(self, status: str) -> None:
        super().__init__(f"{status!r} is not a valid combination status")
        self.status = status
