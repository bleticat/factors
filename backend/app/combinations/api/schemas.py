from pydantic import BaseModel, Field


class PatchCombinationRequest(BaseModel):
    status: str | None = None
    output: str | None = None
    impossible_reason: str | None = None


class BulkFilterRequest(BaseModel):
    status: str | None = None
    factor_values: list[tuple[int, int]] = Field(default_factory=list)


class BulkPatchRequest(BaseModel):
    status: str | None = None
    output: str | None = None
    impossible_reason: str | None = None


class BulkPatchCombinationsRequest(BaseModel):
    filter: BulkFilterRequest = Field(default_factory=BulkFilterRequest)
    patch: BulkPatchRequest = Field(default_factory=BulkPatchRequest)


class EvaluateRequest(BaseModel):
    assignment: list[tuple[int, int]] = Field(default_factory=list)
    limit: int = 50
    offset: int = 0
