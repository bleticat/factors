from abc import ABC, abstractmethod


class GenerationJobReader(ABC):
    @abstractmethod
    async def list_stale_running(self) -> list[int]: ...
