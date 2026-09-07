"""Request bodies for the `decision_tables` REST API. Per ADR 007, routers
using these only parse input, build a typed mediator request, and serialize
the result — no business logic lives here."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateDecisionTableRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateDecisionTableRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AddFactorRequest(BaseModel):
    name: str


class UpdateFactorRequest(BaseModel):
    name: str | None = None
    order_index: int | None = None


class AddFactorValueRequest(BaseModel):
    value: str


class UpdateFactorValueRequest(BaseModel):
    value: str | None = None
    order_index: int | None = None


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
