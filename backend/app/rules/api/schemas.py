"""Request bodies for the `rules` module's REST endpoints. Per ADR 007,
routers using these only parse input, build a typed mediator request, and
serialize the result — no business logic lives here."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateRuleRequest(BaseModel):
    factor_values: list[tuple[int, int]] = Field(default_factory=list)
    output: str
    title: str | None = None


class UpdateRuleRequest(BaseModel):
    output: str | None = None
    title: str | None = None
    factor_values: list[tuple[int, int]] | None = None


class ReorderRulesRequest(BaseModel):
    ordered_rule_ids: list[int] = Field(default_factory=list)
