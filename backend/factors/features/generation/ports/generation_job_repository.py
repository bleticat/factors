from abc import ABC, abstractmethod

from factors.features.generation.entities import GenerationJob


class GenerationJobRepository(ABC):
    @abstractmethod
    async def add(self, job: GenerationJob) -> GenerationJob: ...

    @abstractmethod
    async def get(self, job_id: int) -> GenerationJob | None: ...

    @abstractmethod
    async def get_for_update(self, job_id: int) -> GenerationJob | None: ...

    @abstractmethod
    async def save(self, job: GenerationJob) -> None: ...

    @abstractmethod
    async def has_active_job(self, table_id: int) -> bool: ...

    @abstractmethod
    async def mark_failed_bulk(self, job_ids: list[int], error_message: str) -> int: ...
