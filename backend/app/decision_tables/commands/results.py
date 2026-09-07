"""Minimal command result shapes.

Per ADR 002's guidance against "return full read-side projections from
every command" (it couples write use cases to screen-specific read needs),
commands return small confirmation/id-bearing DTOs of their own rather than
reusing the nested query-side DTOs in `ports/decision_table_queries.py`.
Callers that need the full picture follow up with a query (ADR 002's
"command, then query" pattern).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DecisionTableRef:
    id: int
    name: str
    description: str | None


@dataclass(frozen=True)
class FactorRef:
    id: int
    name: str
    order_index: int


@dataclass(frozen=True)
class FactorValueRef:
    id: int
    value: str
    order_index: int


@dataclass(frozen=True)
class GenerationJobRef:
    id: int
    decision_table_id: int
    status: str
    total_combinations: int
    created_count: int
    error_message: str | None = None


@dataclass(frozen=True)
class CombinationRef:
    id: int
    status: str
    output: str | None
    impossible_reason: str | None


@dataclass(frozen=True)
class BulkPatchResult:
    matched_count: int
    updated_count: int


@dataclass(frozen=True)
class RuleRef:
    id: int
    matched_count: int
    applied_at: datetime | None


@dataclass(frozen=True)
class RuleApplyRef:
    rule_id: int
    matched_count: int
    applied_at: datetime


@dataclass(frozen=True)
class ReapplyRulesResult:
    results: list[RuleApplyRef]
