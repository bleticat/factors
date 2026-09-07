"""The mediator: the single application-facing entrypoint for use cases (ADR 007).

Registries are explicit `dict[type, factory]` wiring built once by the
composition root (`app/composition.py`) — no reflection, no DI container, no
string-based routing. Boundary layers (API routers, the background
generation loop, startup lifecycle hooks) only ever call `mediator.execute`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

from app.shared.database.port import Database, ReadScope, UnitOfWork
from app.shared.errors import UnregisteredRequestError
from app.shared.mediator.requests import Command, Query, Request

TResult = TypeVar("TResult")


class CommandHandler(Protocol[TResult]):
    async def handle(self, request: Command[TResult]) -> TResult: ...


class QueryHandler(Protocol[TResult]):
    async def handle(self, request: Query[TResult]) -> TResult: ...


CommandHandlerFactory = Callable[[UnitOfWork], CommandHandler]
QueryHandlerFactory = Callable[[ReadScope], QueryHandler]


class Mediator:
    def __init__(
        self,
        database: Database,
        command_registry: dict[type, CommandHandlerFactory],
        query_registry: dict[type, QueryHandlerFactory],
    ) -> None:
        self._database = database
        self._command_registry = command_registry
        self._query_registry = query_registry

    async def execute(self, request: Request[TResult]) -> TResult:
        if isinstance(request, Command):
            return await self._execute_command(request)
        if isinstance(request, Query):
            return await self._execute_query(request)
        raise TypeError(f"Request must be a Command or Query, got {type(request)!r}")

    async def _execute_command(self, request: Command[TResult]) -> TResult:
        factory = self._command_registry.get(type(request))
        if factory is None:
            raise UnregisteredRequestError(type(request))
        async with self._database.unit_of_work() as uow:
            handler = factory(uow)
            return await handler.handle(request)

    async def _execute_query(self, request: Query[TResult]) -> TResult:
        factory = self._query_registry.get(type(request))
        if factory is None:
            raise UnregisteredRequestError(type(request))
        async with self._database.read_scope() as scope:
            handler = factory(scope)
            return await handler.handle(request)
