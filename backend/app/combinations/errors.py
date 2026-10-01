from app.shared.errors import ValidationError


class InvalidCombinationStatusError(ValidationError):
    """Raised when a status string doesn't match a `CombinationStatus` member."""

    def __init__(self, status: str) -> None:
        super().__init__(f"{status!r} is not a valid combination status")
        self.status = status
