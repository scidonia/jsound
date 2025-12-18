"""
Tests for enhanced explanation features in JSoundAPI.

Tests the new explanation functionality integrated into the main API
including constraint identification, recommendations, and formatting.
"""

import pytest


def test_explanations_enabled_by_default(api):
    """Test that explanations are enabled by default in JSoundAPI."""
    # api fixture uses default settings
    producer = {
        "type": "array",
        "items": {"type": "number", "minimum": 0, "maximum": 10},
    }
    consumer = {"type": "array", "contains": {"type": "number", "minimum": 50}}

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    assert result.has_explanations()
    assert result.explanation is not None
    assert result.failed_constraints is not None
    assert len(result.failed_constraints) > 0


def test_explanations_can_be_disabled():
    """Test that explanations can be disabled via configuration."""
    from jsound.api import JSoundAPI

    api_no_explanations = JSoundAPI(explanations=False)

    producer = {
        "type": "array",
        "items": {"type": "number", "minimum": 0, "maximum": 10},
    }
    consumer = {"type": "array", "contains": {"type": "number", "minimum": 50}}

    result = api_no_explanations.check_subsumption(producer, consumer)

    assert not result.is_compatible
    assert not result.has_explanations()
    assert result.explanation is None
    assert result.failed_constraints is None
    assert result.recommendations is None


def test_contains_number_range_explanation(api):
    """Test detailed explanation for contains number range failure."""
    producer = {
        "type": "array",
        "items": {"type": "number", "minimum": 0, "maximum": 100},
    }
    consumer = {"type": "array", "contains": {"type": "number", "minimum": 50}}

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    assert "Array contains no elements satisfying" in result.explanation
    assert "{type: number, ≥50}" in result.explanation

    assert "contains:{type: number, ≥50}" in result.failed_constraints

    assert len(result.recommendations) >= 1
    assert "Change producer items minimum from 0 to 50" in result.recommendations


def test_contains_string_length_explanation(api):
    """Test explanation for contains string length failure."""
    producer = {
        "type": "array",
        "items": {"type": "string"},  # Allows empty strings
    }
    consumer = {"type": "array", "contains": {"type": "string", "minLength": 1}}

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    assert "Array contains no elements satisfying" in result.explanation
    assert "{type: string, length ≥1}" in result.explanation

    assert "contains:{type: string, length ≥1}" in result.failed_constraints


def test_object_missing_required_property_explanation(api):
    """Test explanation for missing required property."""
    producer = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }
    consumer = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
        "required": ["name", "email"],
    }

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    assert "Missing required property 'email'" in result.explanation

    assert "required:email" in result.failed_constraints

    assert len(result.recommendations) >= 1
    assert "Add 'email' to producer's required properties" in result.recommendations


def test_array_length_explanation(api):
    """Test explanation for array length constraint failures."""
    producer = {
        "type": "array",
        "items": {"type": "string"},
        # No minItems constraint
    }
    consumer = {"type": "array", "items": {"type": "string"}, "minItems": 3}

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    # Should show array length issue if counterexample has < 3 items
    if result.counterexample and len(result.counterexample) < 3:
        assert "Array too short" in result.explanation
        assert "minItems:3" in result.failed_constraints


def test_additional_properties_explanation(api):
    """Test explanation for additionalProperties conflicts."""
    producer = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "additionalProperties": True,  # Allows extra properties
    }
    consumer = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,  # Forbids extra properties
    }

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    # The counterexample should show extra properties
    if result.counterexample and any(
        key not in ["name"] for key in result.counterexample.keys()
    ):
        assert "Extra properties not allowed" in result.explanation
        assert "additionalProperties:false" in result.failed_constraints


def test_explanation_methods():
    """Test SubsumptionResult explanation methods."""
    from jsound.api import SubsumptionResult

    # Test result with explanations
    result_with_explanations = SubsumptionResult(
        is_compatible=False,
        counterexample=[5],
        explanation="Array contains no elements satisfying {type: number, ≥50}",
        failed_constraints=["contains:{type: number, ≥50}"],
        recommendations=["Change producer items minimum from 0 to 50"],
    )

    assert result_with_explanations.has_explanations()

    detailed = result_with_explanations.get_detailed_explanation()
    assert "Explanation: Array contains no elements satisfying" in detailed
    assert "Failed constraints: contains:{type: number, ≥50}" in detailed
    assert "Recommendations:" in detailed
    assert "• Change producer items minimum from 0 to 50" in detailed

    # Test result without explanations
    result_without_explanations = SubsumptionResult(
        is_compatible=False, counterexample=[5]
    )

    assert not result_without_explanations.has_explanations()
    assert (
        "No detailed explanation available"
        in result_without_explanations.get_detailed_explanation()
    )


def test_compatible_case_no_explanations(api):
    """Test that compatible cases don't generate explanations."""
    producer = {"type": "array", "items": {"type": "string"}}
    consumer = {"type": "array", "items": {"type": "string"}}

    result = api.check_subsumption(producer, consumer)

    assert result.is_compatible
    assert not result.has_explanations()
    assert result.explanation is None
    assert result.failed_constraints is None
    assert result.recommendations is None


def test_error_case_no_explanations(api):
    """Test that error cases don't generate explanations."""
    # Test with an invalid schema that might cause errors
    producer = {"type": "invalid_type"}  # Invalid type
    consumer = {"type": "string"}

    result = api.check_subsumption(producer, consumer)

    # Should handle gracefully without explanations for error cases
    if result.error_message:
        assert not result.has_explanations()


@pytest.mark.contains
def test_mixed_type_anyof_explanation(api):
    """Test explanation for anyOf mixed types with contains."""
    producer = {
        "type": "array",
        "items": {"anyOf": [{"type": "string"}, {"type": "number"}]},
    }
    consumer = {"type": "array", "contains": {"type": "string"}}

    result = api.check_subsumption(producer, consumer)

    assert not result.is_compatible
    assert "Array contains no elements satisfying" in result.explanation
    assert "contains:{type: string}" in result.failed_constraints

    # Should recommend ensuring at least one string element
    recommendations_text = " ".join(result.recommendations)
    assert "string element" in recommendations_text.lower()


def test_backward_compatibility_with_existing_tests():
    """Test that existing code using old API continues to work."""
    from jsound.api import JSoundAPI

    # Old style usage (should still work)
    api = JSoundAPI(timeout=10)  # Don't specify explanations

    producer = {"type": "string"}
    consumer = {"type": "number"}

    result = api.check_subsumption(producer, consumer)

    # Basic functionality should work
    assert not result.is_compatible
    assert hasattr(result, "is_compatible")
    assert hasattr(result, "counterexample")
    assert hasattr(result, "solver_time")

    # New explanation fields should exist but might be None based on default
    assert hasattr(result, "explanation")
    assert hasattr(result, "failed_constraints")
    assert hasattr(result, "recommendations")
