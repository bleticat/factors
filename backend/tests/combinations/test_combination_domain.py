import itertools

import pytest

from factors.features.combinations.entities import (
    CombinationStatus,
    build_signature,
    decompose_index,
    parse_status,
    total_combinations,
)
from factors.shared.errors import ValidationError


def test_parse_status_parses_a_valid_status():
    assert parse_status("possible") == CombinationStatus.POSSIBLE


def test_parse_status_rejects_an_unknown_status():
    with pytest.raises(ValidationError):
        parse_status("bogus")


def test_total_combinations_multiplies_value_counts():
    assert total_combinations([3, 3, 2]) == 18


def test_total_combinations_zero_if_any_factor_has_no_values():
    assert total_combinations([3, 0, 2]) == 0


def test_total_combinations_zero_if_no_factors():
    assert total_combinations([]) == 0


def test_decompose_index_matches_itertools_product_order():
    value_counts = [3, 3, 2]
    expected = list(itertools.product(range(3), range(3), range(2)))
    actual = [
        tuple(decompose_index(i, value_counts))
        for i in range(total_combinations(value_counts))
    ]
    assert actual == expected


def test_decompose_index_matches_itertools_product_for_uneven_counts():
    value_counts = [2, 5, 3, 1]
    expected = list(itertools.product(*(range(n) for n in value_counts)))
    actual = [
        tuple(decompose_index(i, value_counts))
        for i in range(total_combinations(value_counts))
    ]
    assert actual == expected


def test_build_signature_is_deterministic_and_order_sensitive():
    assert build_signature([1, 2, 3]) == "1-2-3"
    assert build_signature([1, 2, 3]) == build_signature([1, 2, 3])
    assert build_signature([3, 2, 1]) != build_signature([1, 2, 3])
