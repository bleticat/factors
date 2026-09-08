"""Pure domain-logic tests — no mediator/database involved. Covers spec
002's regression case: mixed-radix cursor decomposition must match
`itertools.product` order exactly."""

from __future__ import annotations

import itertools

from app.combinations.entities import (
    build_signature,
    decompose_index,
    total_combinations,
)


def test_total_combinations_multiplies_value_counts():
    assert total_combinations([3, 3, 2]) == 18


def test_total_combinations_zero_if_any_factor_has_no_values():
    assert total_combinations([3, 0, 2]) == 0


def test_total_combinations_zero_if_no_factors():
    assert total_combinations([]) == 0


def test_decompose_index_matches_itertools_product_order():
    value_counts = [3, 3, 2]
    expected = list(itertools.product(range(3), range(3), range(2)))
    actual = [tuple(decompose_index(i, value_counts)) for i in range(total_combinations(value_counts))]
    assert actual == expected


def test_decompose_index_matches_itertools_product_for_uneven_counts():
    value_counts = [2, 5, 3, 1]
    expected = list(itertools.product(*(range(n) for n in value_counts)))
    actual = [tuple(decompose_index(i, value_counts)) for i in range(total_combinations(value_counts))]
    assert actual == expected


def test_build_signature_is_deterministic_and_order_sensitive():
    assert build_signature([1, 2, 3]) == "1-2-3"
    assert build_signature([1, 2, 3]) == build_signature([1, 2, 3])
    assert build_signature([3, 2, 1]) != build_signature([1, 2, 3])
