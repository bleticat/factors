"""Request bodies for the `rules` module's REST endpoints. Routers using
these only parse input, call the module's command/query service, and
serialize the result — no business logic lives here."""

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
