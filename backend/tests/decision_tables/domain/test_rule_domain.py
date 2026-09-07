"""Pure domain-logic tests for the spec 007 generality check — no
mediator/database involved."""

from __future__ import annotations

from app.decision_tables.domain.rule import RuleAssignment, is_at_least_as_general


def _pairs(*pairs: tuple[int, int]) -> list[RuleAssignment]:
    return [RuleAssignment(factor_id=f, factor_value_id=v) for f, v in pairs]


def test_empty_assignment_is_at_least_as_general_as_anything():
    assert is_at_least_as_general(_pairs(), _pairs((1, 1)))
    assert is_at_least_as_general(_pairs(), _pairs((1, 1), (2, 2)))
    assert is_at_least_as_general(_pairs(), _pairs())


def test_equal_assignments_are_at_least_as_general_as_each_other():
    assert is_at_least_as_general(_pairs((1, 1)), _pairs((1, 1)))


def test_superset_assignment_is_not_at_least_as_general():
    # (1,1),(2,2) is a strict refinement of (1,1) — not "at least as general".
    assert not is_at_least_as_general(_pairs((1, 1), (2, 2)), _pairs((1, 1)))


def test_subset_assignment_is_at_least_as_general():
    assert is_at_least_as_general(_pairs((1, 1)), _pairs((1, 1), (2, 2)))


def test_incomparable_assignments_are_not_at_least_as_general_either_way():
    assert not is_at_least_as_general(_pairs((1, 1)), _pairs((2, 2)))
    assert not is_at_least_as_general(_pairs((2, 2)), _pairs((1, 1)))
