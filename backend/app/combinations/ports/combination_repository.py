from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.combinations.entities import Combination, CombinationStatus


@dataclass(frozen=True)
class FactorValueAssignment:
    factor_id: int
    factor_value_id: int


@dataclass(frozen=True)
class CombinationFilter:
    status: CombinationStatus | None = None
    factor_values: tuple[FactorValueAssignment, ...] = ()


@dataclass(frozen=True)
class CombinationPatch:
    status: CombinationStatus | None = None
    output: str | None = None
    output_set: bool = False
    impossible_reason: str | None = None
    impossible_reason_set: bool = False


class CombinationRepository(ABC):
    @abstractmethod
    async def bulk_insert(self, combinations: list[Combination]) -> None: ...

    @abstractmethod
    async def get(self, table_id: int, combination_id: int) -> Combination | None: ...

    @abstractmethod
    async def save(self, combination: Combination) -> None: ...

    @abstractmethod
    async def bulk_update_status(
        self, table_id: int, filter_: CombinationFilter, patch: CombinationPatch
    ) -> tuple[int, int]: ...

    @abstractmethod
    async def delete_all_for_table(self, table_id: int) -> None: ...
