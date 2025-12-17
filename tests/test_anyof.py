"""
Boolean composition subsumption tests.

Tests for JSON Schema boolean composition including:
- anyOf subsumption relationships
- oneOf subsumption relationships
- allOf subsumption relationships
- Mixed composition scenarios
"""

import pytest


@pytest.mark.anyof
@pytest.mark.subsumption
def test_anyof_subset_subsumption(api, composition_schemas):
    """Test that smaller anyOf is subsumed by larger anyOf."""
    result = api.check_subsumption(
        composition_schemas["string_or_integer"],
        composition_schemas["string_number_boolean"],
    )
    assert result.is_compatible, (
        "String|integer should be subsumed by string|number|boolean"
    )


@pytest.mark.anyof
@pytest.mark.anti_subsumption
def test_anyof_superset_anti_subsumption(api, composition_schemas):
    """Test that larger anyOf is NOT subsumed by smaller anyOf."""
    result = api.check_subsumption(
        composition_schemas["string_number_boolean"],
        composition_schemas["string_or_integer"],
    )
    assert not result.is_compatible, (
        "Superset anyOf should not be subsumed by subset anyOf"
    )


@pytest.mark.anyof
@pytest.mark.subsumption
def test_anyof_compatible_types_subsumption(api, composition_schemas):
    """Test anyOf with compatible types."""
    # string|number should be subsumed by string|number (same)
    result = api.check_subsumption(
        composition_schemas["string_or_number"], composition_schemas["string_or_number"]
    )
    assert result.is_compatible, "Same anyOf schemas should be compatible"


@pytest.mark.allof
@pytest.mark.anti_subsumption
def test_simple_not_subsumes_allof(api, composition_schemas, object_schemas):
    """Test that simple schema does not subsume allOf consumer."""
    simple_schema = {"type": "object", "properties": {"value": {"type": "integer"}}}

    result = api.check_subsumption(simple_schema, composition_schemas["strict_allof"])
    assert not result.is_compatible, (
        "Simple object should not be subsumed by strict allOf requiring multiple properties"
    )


@pytest.mark.subsumption
def test_allof_subsumes_individual_parts(api, composition_schemas):
    """Test that allOf schema subsumes individual parts."""
    individual_part = {"type": "object", "properties": {"value": {"type": "integer"}}}

    result = api.check_subsumption(composition_schemas["strict_allof"], individual_part)
    assert result.is_compatible, "AllOf should subsume individual constraint parts"


@pytest.mark.parametrize(
    "producer,consumer,expected,description",
    [
        (
            {"anyOf": [{"type": "string"}, {"type": "integer"}]},
            {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "boolean"}]},
            True,
            "AnyOf producer should be subsumed by broader anyOf consumer",
        ),
        (
            {"anyOf": [{"type": "number"}]},
            {"anyOf": [{"type": "integer"}]},
            False,  # Z3 correctly returns False - number should not subsume integer
            "AnyOf with number should not subsume anyOf with integer",
        ),
        (
            {"type": "string"},
            {"anyOf": [{"type": "string"}, {"type": "number"}]},
            True,
            "Single type should subsume anyOf containing that type",
        ),
        (
            {"anyOf": [{"type": "string"}, {"type": "number"}]},
            {"type": "string"},
            False,  # Z3 correctly returns False - anyOf should not subsume stricter type
            "AnyOf should not subsume single stricter type",
        ),
    ],
)
def test_composition_relationships(api, producer, consumer, expected, description):
    """Parametrized tests for boolean composition relationships."""
    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible == expected, f"Failed: {description}"


@pytest.mark.anyof
def test_manual_anyof_subsumption(api):
    """Test manually defined anyOf subsumption."""
    # Producer that accepts strings or integers
    producer = {"anyOf": [{"type": "string"}, {"type": "integer"}]}

    # Consumer that accepts strings, integers, or booleans
    consumer = {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "boolean"}]}

    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, (
        "AnyOf producer should be subsumed by broader anyOf consumer"
    )


@pytest.mark.oneOf
def test_oneof_basic_subsumption(api, composition_schemas):
    """Test basic oneOf subsumption."""
    # oneOf should behave similarly to anyOf for subsumption
    oneof_schema = composition_schemas["simple_oneof"]

    # Test self-subsumption
    result = api.check_subsumption(oneof_schema, oneof_schema)
    assert result.is_compatible, "OneOf schema should subsume itself"


@pytest.mark.allof
def test_allof_strict_requirements(api):
    """Test that allOf requires all constraints to be satisfied."""
    # Producer with single constraint
    simple_producer = {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
    }

    # Consumer with multiple constraints (allOf)
    allof_consumer = {
        "allOf": [
            {"type": "object", "properties": {"value": {"type": "integer"}}},
            {
                "type": "object",
                "required": ["value", "name"],
                "properties": {"name": {"type": "string"}},
            },
        ]
    }

    result = api.check_subsumption(simple_producer, allof_consumer)
    assert not result.is_compatible, (
        "Superset anyOf should not be subsumed by subset anyOf"
    )
