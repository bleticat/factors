"""Decorator for a use-case method whose entire body is one
`self._database.unit_of_work()` transaction (see `ports/database.py` and
`ports/unit_of_work.py`). Write:

    @uow
    async def delete_decision_table(self, table_id: int, *, uow: UnitOfWork) -> None:
        await uow.tables.delete(table_id)

instead of making `async with self._database.unit_of_work() as uow: ...`
the method's only top-level statement — same commit-on-return,
rollback-on-exception behavior, just without repeating the `async with`
line in every method. `uow` is keyword-only and always last: the
decorator injects it, callers never pass it, so it stays visually
separate from the method's actual business parameters rather than
crowding in as the first one. Doesn't fit a method that needs to do
anything (validate, read elsewhere) before or after the transaction, or
that opens more than one transaction over its body — those stay written
out by hand.
"""

from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

R = TypeVar("R")


def uow(method: Callable[..., Awaitable[R]]) -> Callable[..., Coroutine[Any, Any, R]]:
    """Open `self._database.unit_of_work()` around a call to `method`,
    passing the open `UnitOfWork` in as its keyword-only `uow` parameter."""

    @wraps(method)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        async with self._database.unit_of_work() as unit_of_work:
            return await method(self, *args, uow=unit_of_work, **kwargs)

    return wrapper
