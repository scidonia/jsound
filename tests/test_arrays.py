"""
Array constraint subsumption tests.

Tests for JSON Schema array constraints including:
- Item type constraints
- Array length constraints (minItems, maxItems)
- Array subsumption relationships
"""

import pytest


@pytest.mark.arrays
@pytest.mark.subsumption
def test_short_array_subsumes_long_array(api, array_schemas):
    """Test that arrays with stricter length constraints subsume looser ones."""
    result = api.check_subsumption(
        array_schemas["short_array"], array_schemas["long_array"]
    )
    assert result.is_compatible, "Short array should be subsumed by long array"


@pytest.mark.arrays
@pytest.mark.anti_subsumption
def test_long_array_not_subsumes_short_array(api, array_schemas):
    """Test that arrays with looser length constraints do not subsume stricter ones."""
    result = api.check_subsumption(
        array_schemas["required_array"], array_schemas["short_array"]
    )
    assert not result.is_compatible, (
        "Array with incompatible constraints should not be subsumed"
        "Test that arrays with same item types are compatible."
        ""
    )
    result = api.check_subsumption(
        array_schemas["string_array"], array_schemas["string_array"]
    )
    assert result.is_compatible, "Arrays with same item types should be compatible"


@pytest.mark.arrays
@pytest.mark.anti_subsumption
def test_different_item_type_incompatibility(api, array_schemas):
    """Test that arrays with different item types are incompatible."""
    result = api.check_subsumption(
        array_schemas["string_array"], array_schemas["number_array"]
    )
    assert not result.is_compatible, (
        "Array with incompatible constraints should not be subsumed"
    )


@pytest.mark.arrays
@pytest.mark.parametrize(
    "producer,consumer,expected,description",
    [
        (
            {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            True,
            "Shorter array subsumes longer array",
        ),
        (
            {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 5,
                "maxItems": 10,
            },
            {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            False,  # Array constraints conflict - should be False with Z3
            "Array constraints conflict",
        ),
        (
            {"type": "array", "items": {"type": "integer"}, "minItems": 1},
            {"type": "array", "items": {"type": "number"}, "minItems": 0},
            True,
            "Array with stricter item type and length constraints",
        ),
    ],
)
def test_array_constraint_relationships(api, producer, consumer, expected, description):
    """Parametrized tests for array constraint relationships."""
    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible == expected, f"Failed: {description}"
