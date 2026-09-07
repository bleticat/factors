from __future__ import annotations

from dataclasses import dataclass

from app.decision_tables.commands.results import CombinationRef
from app.decision_tables.domain.combination import parse_status
from app.decision_tables.domain.errors import CombinationNotFoundError
from app.decision_tables.ports.combination_repository import CombinationRepository
from app.shared.mediator.requests import Command


@dataclass(frozen=True)
class PatchCombinationCommand(Command[CombinationRef]):
    table_id: int
    combination_id: int
    status: str | None = None
    output: str | None = None
    output_set: bool = False
    impossible_reason: str | None = None
    impossible_reason_set: bool = False


class PatchCombinationHandler:
    def __init__(self, combinations: CombinationRepository) -> None:
        self._combinations = combinations

    async def handle(self, request: PatchCombinationCommand) -> CombinationRef:
        combination = await self._combinations.get(request.table_id, request.combination_id)
        if combination is None:
            raise CombinationNotFoundError(request.combination_id)

        if request.status is not None:
            combination.status = parse_status(request.status)
        if request.output_set:
            combination.output = request.output
        if request.impossible_reason_set:
            combination.impossible_reason = request.impossible_reason

        await self._combinations.save(combination)
        assert combination.id is not None
        return CombinationRef(
            id=combination.id,
            status=str(combination.status),
            output=combination.output,
            impossible_reason=combination.impossible_reason,
        )
