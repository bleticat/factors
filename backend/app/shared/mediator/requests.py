"""Base request types.

Per ADR 002 / ADR 007, every use case is a typed, data-only Command or Query.
Handlers dispatch on the concrete request's class, and the mediator dispatches
on whether the request is a Command (write, runs in a unit of work) or a
Query (read, runs in a read scope) via isinstance checks against these two
marker base classes.
"""

from __future__ import annotations

from typing import Generic, TypeVar

TResult = TypeVar("TResult")


class Request(Generic[TResult]):
    """Marker base for anything the mediator can execute."""


class Command(Request[TResult]):
    """A data-only request that changes state. Executed inside a unit of work
    (one command dispatch = one transaction; commit on success, rollback on
    failure)."""


class Query(Request[TResult]):
    """A data-only request that reads state. Executed inside a read scope
    (no write transaction)."""
