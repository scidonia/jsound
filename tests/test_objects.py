"""
Object property subsumption tests.

Tests for JSON Schema object constraints including:
- Required properties
- Additional properties
- Property type constraints
- Object subsumption relationships
"""

import pytest


@pytest.mark.objects
@pytest.mark.subsumption
def test_strict_object_subsumes_flexible(api, object_schemas):
    """Test that objects with stricter constraints subsume flexible ones."""
    result = api.check_subsumption(
        object_schemas["strict_object"], object_schemas["flexible_object"]
    )
    assert result.is_compatible, "Strict object should be subsumed by flexible object"


@pytest.mark.objects
@pytest.mark.anti_subsumption
def test_flexible_object_not_subsumes_strict(api, object_schemas):
    """Test that flexible objects do not subsume strict ones."""
    result = api.check_subsumption(
        object_schemas["flexible_object"], object_schemas["strict_object"]
    )
    assert not result.is_compatible, (
        "Object with incompatible constraints should not be subsumed"
    )


@pytest.mark.subsumption
def test_more_required_subsumes_fewer_required(api, object_schemas):
    """Test that objects with more required properties subsume those with fewer."""
    result = api.check_subsumption(
        object_schemas["required_name_email"], object_schemas["required_name"]
    )
    assert result.is_compatible, (
        "More required fields should subsume fewer required fields"
    )


@pytest.mark.objects
@pytest.mark.anti_subsumption
def test_fewer_required_not_subsumes_more_required(api, object_schemas):
    """Test that objects with fewer required properties do not subsume those with more."""
    result = api.check_subsumption(
        object_schemas["required_name"], object_schemas["required_name_email"]
    )
    assert not result.is_compatible, (
        "Object with incompatible constraints should not be subsumed"
    )


@pytest.mark.objects
@pytest.mark.subsumption
def test_nested_object_subsumption(api, nested_schemas):
    """Test deeply nested object subsumption."""
    result = api.check_subsumption(
        nested_schemas["nested_producer"], nested_schemas["nested_consumer"]
    )
    assert result.is_compatible, "Nested producer should be subsumed by nested consumer"


@pytest.mark.objects
@pytest.mark.parametrize(
    "producer,consumer,expected,description",
    [
        (
            {
                "type": "object",
                "required": ["a", "b"],
                "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            },
            {
                "type": "object",
                "required": ["a"],
                "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            },
            True,
            "More required fields subsume fewer required fields",
        ),
        (
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "additionalProperties": True,
            },
            True,
            "Strict object subsumes flexible object",
        ),
        (
            {"type": "object", "additionalProperties": True},
            {"type": "object", "additionalProperties": False},
            False,  # Z3 correctly returns False - flexible does not subsume strict
            "Flexible object does not subsume strict object",
        ),
    ],
)
def test_object_constraint_relationships(
    api, producer, consumer, expected, description
):
    """Parametrized tests for object constraint relationships."""
    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible == expected, f"Failed: {description}"
