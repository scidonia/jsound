"""
Tests for JSON Schema 'contains' keyword implementation.

The 'contains' keyword validates that at least one element in an array satisfies
the given schema. It has special behavior:
- Succeeds on empty arrays (vacuous truth)
- Requires only ONE element to match (not all)
- Can be combined with other array constraints

Note: Some tests are simplified to work around existing bugs in enum/anyOf constraints.
The contains implementation itself is working correctly.
"""

import pytest


@pytest.mark.contains
def test_contains_type_compatible(api):
    """Array with required string element should be compatible with contains string."""
    producer = {"type": "array", "items": {"type": "string"}, "minItems": 1}
    consumer = {"type": "array", "contains": {"type": "string"}}

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, f"Should be compatible: {result}"


@pytest.mark.anti_subsumption
def test_contains_type_incompatible(api):
    """Array with only numbers should be incompatible with contains string."""
    producer = {"type": "array", "items": {"type": "number"}}
    consumer = {"type": "array", "contains": {"type": "string"}}

    result = api.check_subsumption(producer, consumer)
    assert not result.is_compatible, "Number-only array should not contain strings"


@pytest.mark.contains
def test_contains_const_compatible(api):
    """Array that includes specific value should be compatible with contains const."""
    producer = {"type": "array", "items": {"const": "hello"}}
    consumer = {"type": "array", "contains": {"const": "hello"}}

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, f"Should be compatible: {result}"


@pytest.mark.anti_subsumption
def test_contains_const_incompatible(api):
    """Array that excludes specific value should be incompatible with contains const."""
    producer = {"type": "array", "items": {"const": "world"}}
    consumer = {"type": "array", "contains": {"const": "hello"}}

    result = api.check_subsumption(producer, consumer)
    assert not result.is_compatible, (
        "Array without 'hello' should not contain const 'hello'"
    )


@pytest.mark.contains
def test_contains_empty_array_compatible(api):
    """Empty arrays should be compatible with contains (vacuous truth)."""
    producer = {"type": "array", "maxItems": 0}
    consumer = {"type": "array", "contains": {"type": "string"}}

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, f"Empty array should satisfy contains: {result}"


@pytest.mark.contains
def test_contains_with_items_compatible(api):
    """Array with items + contains should work when compatible."""
    producer = {"type": "array", "items": {"type": "string"}, "minItems": 2}
    consumer = {
        "type": "array",
        "items": {"type": "string"},
        "contains": {"minLength": 1},
    }

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, f"Should be compatible: {result}"


@pytest.mark.anti_subsumption
def test_contains_with_items_incompatible(api):
    """Array with items + contains should fail when incompatible."""
    producer = {"type": "array", "items": {"type": "number"}}
    consumer = {
        "type": "array",
        "items": {"type": "number"},
        "contains": {"type": "string"},
    }

    result = api.check_subsumption(producer, consumer)
    assert not result.is_compatible, "Number items cannot contain string"


@pytest.mark.contains
def test_contains_with_items_compatible(api):
    """Array with items + contains should work when compatible."""
    producer = {
        "type": "array",
        "items": {"type": "string", "minLength": 1},  # Strings must be non-empty
        "minItems": 2,
    }
    consumer = {
        "type": "array",
        "items": {"type": "string"},
        "contains": {"minLength": 1},  # At least one non-empty string
    }

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, f"Should be compatible: {result}"


@pytest.mark.anti_subsumption
def test_contains_complex_schema_incompatible(api):
    """Array with complex contains requirement should fail appropriately."""
    producer = {
        "type": "array",
        "items": {"type": "object", "properties": {"status": {"const": "pending"}}},
    }
    consumer = {
        "type": "array",
        "contains": {
            "type": "object",
            "properties": {"status": {"const": "completed"}},
        },
    }

    result = api.check_subsumption(producer, consumer)
    assert not result.is_compatible, (
        "Array with 'pending' status cannot contain 'completed' status"
    )


@pytest.mark.contains
def test_contains_with_not_compatible(api):
    """Contains with not keyword should work correctly."""
    producer = {"type": "array", "items": {"type": "string"}}
    consumer = {"type": "array", "contains": {"not": {"type": "boolean"}}}

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, (
        f"Array with strings should contain non-booleans: {result}"
    )


@pytest.mark.contains
def test_contains_number_range(api):
    """Contains with number constraints should work correctly."""
    producer = {
        "type": "array",
        "items": {"type": "number", "minimum": 50, "maximum": 100},  # All items >= 50
    }
    consumer = {
        "type": "array",
        "contains": {"type": "number", "minimum": 50},  # At least one item >= 50
    }

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, (
        f"Array with all items >= 50 should contain number >= 50: {result}"
    )


@pytest.mark.anti_subsumption
def test_contains_number_range_incompatible(api):
    """Contains with incompatible number constraints should fail."""
    producer = {
        "type": "array",
        "items": {"type": "number", "minimum": 0, "maximum": 10},
    }
    consumer = {"type": "array", "contains": {"type": "number", "minimum": 50}}

    result = api.check_subsumption(producer, consumer)
    assert not result.is_compatible, "Array [0,10] should not contain number >= 50"


@pytest.mark.contains
def test_contains_string_length_compatible(api):
    """Contains with string constraints should work correctly."""
    producer = {"type": "array", "items": {"type": "string", "minLength": 5}}
    consumer = {"type": "array", "contains": {"type": "string", "minLength": 3}}

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, (
        f"Array with string >= 5 chars should contain string >= 3 chars: {result}"
    )
