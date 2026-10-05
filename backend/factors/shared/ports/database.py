from contextlib import AbstractAsyncContextManager
from typing import Protocol

from factors.features.combinations.ports.combination_reader import CombinationReader
from factors.features.combinations.ports.combination_repository import (
    CombinationRepository,
)
from factors.features.generation.ports.generation_job_reader import GenerationJobReader
from factors.features.generation.ports.generation_job_repository import (
    GenerationJobRepository,
)
from factors.features.rules.ports.rule_reader import RuleReader
from factors.features.rules.ports.rule_repository import RuleRepository
from factors.features.tables.ports.decision_table_reader import DecisionTableReader
from factors.features.tables.ports.decision_table_repository import (
    DecisionTableRepository,
)


class DataAccess(Protocol):
    tables: DecisionTableRepository
    jobs: GenerationJobRepository
    combinations: CombinationRepository
    rules: RuleRepository

    tables_reader: DecisionTableReader
    combinations_reader: CombinationReader
    rules_reader: RuleReader
    jobs_reader: GenerationJobReader


class Database(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[DataAccess]: ...

    def snapshot(self) -> AbstractAsyncContextManager[DataAccess]: ...
