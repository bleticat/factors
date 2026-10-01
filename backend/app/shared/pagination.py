"""Shared pagination request/response shapes for query results."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


@dataclass(frozen=True)
class PageRequest:
    """A page of results to request: `limit` items starting at `offset`."""

    limit: int = DEFAULT_LIMIT
    offset: int = 0

    def __post_init__(self) -> None:
        """Validate `limit` and `offset`.

        Raises:
            ValueError: if `limit` is outside `[1, MAX_LIMIT]` or `offset` is negative.
        """
        if self.limit < 1 or self.limit > MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
        if self.offset < 0:
            raise ValueError("offset must be >= 0")


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of query results, with enough to compute further pages."""

    items: Sequence[T]
    total: int
    limit: int
    offset: int
