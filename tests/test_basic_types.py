"""
Basic type subsumption tests.

Tests for fundamental JSON Schema type constraints including:
- Type compatibility (integer ⊆ number)
- Numeric ranges and constraints
- String patterns and length constraints
- Constants and enums
"""

import pytest


@pytest.mark.subsumption
def test_integer_subsumes_number(api, basic_types):
    """Test that integer type is subsumed by number type."""
    result = api.check_subsumption(basic_types["integer"], basic_types["number"])
    assert result.is_compatible, "Integer should be subsumed by number"


@pytest.mark.anti_subsumption
def test_number_not_subsumes_integer(api, basic_types):
    """Test that number type is NOT subsumed by integer type."""
    result = api.check_subsumption(basic_types["number"], basic_types["integer"])
    assert not result.is_compatible, "Number should not be subsumed by integer"


@pytest.mark.numbers
@pytest.mark.anti_subsumption
def test_salary_range_anti_subsumption(api, number_schemas):
    """Test that wide salary range is NOT subsumed by narrow salary range."""
    result = api.check_subsumption(
        number_schemas["general_salary"], number_schemas["junior_salary"]
    )
    assert not result.is_compatible, (
        "General salary range [30k-200k] should not be subsumed by junior salary range [40k-60k]"
    )
    assert result.counterexample is not None, "Should provide a counterexample"


@pytest.mark.strings
@pytest.mark.anti_subsumption
def test_string_length_anti_subsumption_short_vs_long(api, string_schemas):
    """Test that short string constraint [1-10] is NOT subsumed by long string [5-100]."""
    result = api.check_subsumption(
        string_schemas["short_string"], string_schemas["long_string"]
    )
    assert not result.is_compatible, (
        "Short string [1-10] should NOT be subsumed by long string [5-100]"
    )
    assert result.counterexample is not None, "Should provide a counterexample"


@pytest.mark.strings
@pytest.mark.anti_subsumption
def test_string_length_anti_subsumption(api, string_schemas):
    """Test that long string constraint [5-100] is NOT subsumed by short string [1-10]."""
    result = api.check_subsumption(
        string_schemas["long_string"], string_schemas["short_string"]
    )
    assert not result.is_compatible, (
        "Long string [5-100] should NOT be subsumed by short string [1-10]"
    )
    assert result.counterexample is not None, "Should provide a counterexample"


@pytest.mark.strings
@pytest.mark.subsumption
def test_enum_subset_subsumption(api, string_schemas):
    """Test that smaller enum is subsumed by larger enum."""
    result = api.check_subsumption(
        string_schemas["enum_colors"], string_schemas["enum_extended"]
    )
    assert result.is_compatible, "Smaller enum should be subsumed by larger enum"


@pytest.mark.strings
@pytest.mark.anti_subsumption
def test_enum_superset_anti_subsumption(api, string_schemas):
    """Test that larger enum is NOT subsumed by smaller enum."""
    result = api.check_subsumption(
        string_schemas["enum_extended"], string_schemas["enum_colors"]
    )
    assert not result.is_compatible, (
        "Larger enum should not be subsumed by smaller enum"
    )


@pytest.mark.subsumption
@pytest.mark.parametrize(
    "producer_type,consumer_type,expected",
    [
        ("integer", "number", True),  # Integer should be subsumed by number
        ("number", "integer", False),  # Number should NOT be subsumed by integer
        ("boolean", "integer", False),  # Boolean should NOT be subsumed by integer
        ("string", "boolean", False),  # String should NOT be subsumed by boolean
        ("string", "string", True),  # Same type should be compatible
        ("boolean", "boolean", True),
        ("string", "number", False),  # String should NOT be subsumed by number
        ("number", "string", False),  # Number should NOT be subsumed by string
    ],
)
def test_basic_type_compatibility(
    api, basic_types, producer_type, consumer_type, expected
):
    """Parametrized test for basic type compatibility."""
    result = api.check_subsumption(
        basic_types[producer_type], basic_types[consumer_type]
    )
    assert result.is_compatible == expected, (
        f"{producer_type} → {consumer_type} compatibility failed"
    )


@pytest.mark.subsumption
@pytest.mark.parametrize(
    "producer,consumer,description",
    [
        ({"type": "integer"}, {"type": "number"}, "Integer subsumes number"),
        (
            {"type": "string", "minLength": 5},
            {"type": "string", "minLength": 3},
            "Stricter string constraint subsumes looser",
        ),
        ({"const": "hello"}, {"type": "string"}, "Constant subsumes general type"),
        (
            {"enum": ["red", "blue"]},
            {"enum": ["red", "blue", "green"]},
            "Smaller enum subsumes larger enum",
        ),
    ],
)
def test_parametrized_subsumption_cases(api, producer, consumer, description):
    """Parametrized tests for valid subsumption cases."""
    result = api.check_subsumption(producer, consumer)
    assert result.is_compatible, f"Failed: {description}"


@pytest.mark.anti_subsumption
@pytest.mark.parametrize(
    "producer,consumer,description",
    [
        ({"type": "number"}, {"type": "integer"}, "Number does not subsume integer"),
        ({"type": "string"}, {"type": "number"}, "Different types are incompatible"),
        (
            {"const": "hello"},
            {"const": "world"},
            "Different constants are incompatible",
        ),
    ],
)
def test_parametrized_anti_subsumption_cases(api, producer, consumer, description):
    """Parametrized tests for invalid subsumption cases."""
    result = api.check_subsumption(producer, consumer)
    assert not result.is_compatible, "Number should not be subsumed by integer"
