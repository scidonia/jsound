#!/usr/bin/env python3
"""
Test cases for JSON Schema 'not' keyword support.

The 'not' keyword represents logical negation - a schema is valid if it does NOT match the negated schema.
This is critical for expressing exclusion constraints and complex validation rules.
"""

import pytest
from jsound.api import check_subsumption


@pytest.mark.subsumption
class TestNotKeyword:
    """Test basic 'not' keyword functionality."""

    def test_not_empty_string_constraint(self, api):
        """Test that 'not' can exclude empty strings effectively."""
        # Producer: must be string AND NOT be empty string
        producer = {
            "type": "object",
            "properties": {
                "name": {"allOf": [{"type": "string"}, {"not": {"const": ""}}]}
            },
            "required": ["name"],
        }

        # Consumer: must be string with minimum length 1
        consumer = {
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 1}},
            "required": ["name"],
        }

        result = api.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer excluding empty string should subsume consumer requiring non-empty string"
        )

    def test_not_with_constrained_positive_assertion(self, api):
        """Test 'not' combined with positive constraints creating compatibility."""
        # Producer: must be positive integer (integer > 0)
        producer = {
            "type": "object",
            "properties": {
                "count": {
                    "allOf": [
                        {"type": "integer"},
                        {"minimum": 1},  # Positive constraint
                    ]
                }
            },
            "required": ["count"],
        }

        # Consumer: must be integer AND NOT be negative or zero
        consumer = {
            "type": "object",
            "properties": {
                "count": {
                    "allOf": [
                        {"type": "integer"},
                        {"not": {"maximum": 0}},  # NOT <= 0 (i.e., > 0)
                    ]
                }
            },
            "required": ["count"],
        }

        result = api.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with positive integers should subsume consumer excluding non-positive integers"
        )

    def test_not_enum_compatibility_with_intersection(self, api):
        """Test 'not' enum creating compatibility when consumer is subset of allowed values."""
        # Producer: priority must be in ["high", "critical", "urgent"]
        producer = {
            "type": "object",
            "properties": {"priority": {"enum": ["high", "critical", "urgent"]}},
            "required": ["priority"],
        }

        # Consumer: priority must NOT be "low" AND must be string
        consumer = {
            "type": "object",
            "properties": {
                "priority": {"allOf": [{"type": "string"}, {"not": {"const": "low"}}]}
            },
            "required": ["priority"],
        }

        result = api.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with specific high priorities should subsume consumer excluding 'low'"
        )

    def test_not_self_subsumption(self, api):
        """Test that 'not' schemas subsume themselves."""
        schema = {
            "type": "object",
            "properties": {
                "value": {"not": {"anyOf": [{"type": "string"}, {"const": 42}]}}
            },
            "required": ["value"],
        }

        result = api.check_subsumption(schema, schema)
        assert result.is_compatible, (
            "'Not' schemas should subsume themselves (self-subsumption)"
        )


@pytest.mark.anti_subsumption
class TestNotKeywordAntiSubsumption:
    """Test cases where 'not' should prevent subsumption."""

    def test_not_excludes_required_type(self, api):
        """Test that 'not' correctly creates incompatibility when excluding required type."""
        # Producer: value must NOT be a string
        producer = {
            "type": "object",
            "properties": {"value": {"not": {"type": "string"}}},
            "required": ["value"],
        }

        # Consumer: value must be a string
        consumer = {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        }

        result = api.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Producer excluding strings should NOT subsume consumer requiring strings"
        )

    def test_not_excludes_required_value(self, api):
        """Test that 'not' correctly blocks required specific values."""
        # Producer: status must NOT be "error"
        producer = {
            "type": "object",
            "properties": {"status": {"not": {"const": "error"}}},
            "required": ["status"],
        }

        # Consumer: status must be exactly "error"
        consumer = {
            "type": "object",
            "properties": {"status": {"const": "error"}},
            "required": ["status"],
        }

        result = api.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Producer excluding 'error' should NOT subsume consumer requiring 'error'"
        )

    def test_not_enum_overlap_conflict(self, api):
        """Test 'not' enum creating conflict when there's overlap."""
        # Producer: status must NOT be "error" or "failed"
        producer = {
            "type": "object",
            "properties": {"status": {"not": {"enum": ["error", "failed"]}}},
            "required": ["status"],
        }

        # Consumer: status can be "error", "success", or "pending"
        consumer = {
            "type": "object",
            "properties": {"status": {"enum": ["error", "success", "pending"]}},
            "required": ["status"],
        }

        result = api.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Producer excluding 'error' should NOT subsume consumer allowing 'error'"
        )

    def test_not_broad_exclusion_incompatible(self, api):
        """Test that broad 'not' exclusions create incompatibility."""
        # Producer: value must NOT be number (excludes all numbers)
        producer = {
            "type": "object",
            "properties": {"value": {"not": {"type": "number"}}},
            "required": ["value"],
        }

        # Consumer: value must be a positive integer
        consumer = {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 1}},
            "required": ["value"],
        }

        result = api.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Producer excluding all numbers should NOT subsume consumer requiring integers"
        )


@pytest.mark.subsumption
class TestNotKeywordComplexScenarios:
    """Test complex 'not' keyword scenarios."""

    def test_not_with_allof_combination(self, api):
        """Test 'not' combined with allOf constraints creating compatibility."""
        # Producer: must be positive integer (>= 1)
        producer = {
            "type": "object",
            "properties": {
                "count": {
                    "allOf": [
                        {"type": "integer"},
                        {"minimum": 1},  # Positive integers
                    ]
                }
            },
            "required": ["count"],
        }

        # Consumer: must be integer AND NOT be negative
        consumer = {
            "type": "object",
            "properties": {
                "count": {
                    "allOf": [
                        {"type": "integer"},
                        {"not": {"maximum": -1}},  # NOT <= -1 (i.e., >= 0)
                    ]
                }
            },
            "required": ["count"],
        }

        result = api.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer (positive integers) should subsume consumer (excluding negative integers)"
        )

    def test_not_double_negation(self, api):
        """Test double negation should work correctly."""
        # Producer: value must NOT NOT be a string (i.e., must be string)
        producer = {
            "type": "object",
            "properties": {"value": {"not": {"not": {"type": "string"}}}},
            "required": ["value"],
        }

        # Consumer: value must be string
        consumer = {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        }

        result = api.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Double negation should be equivalent to positive assertion"
        )

    def test_not_with_format_compatibility(self, api):
        """Test 'not' format creating compatibility in the right direction."""
        # Producer: must be string with uri format
        producer = {
            "type": "object",
            "properties": {"identifier": {"type": "string", "format": "uri"}},
            "required": ["identifier"],
        }

        # Consumer: must be string but NOT email format
        consumer = {
            "type": "object",
            "properties": {
                "identifier": {
                    "allOf": [{"type": "string"}, {"not": {"format": "email"}}]
                }
            },
            "required": ["identifier"],
        }

        result = api.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with uri format should subsume consumer excluding email format"
        )


# Manual test examples for demonstration
if __name__ == "__main__":
    print("=" * 70)
    print("JSON Schema 'not' Keyword Tests")
    print("Testing logical negation constraints")
    print("=" * 70)

    from jsound.api import JSoundAPI

    api = JSoundAPI()

    # Example 1: Empty string exclusion
    print("\n1. Empty String Exclusion:")
    producer = {
        "type": "object",
        "properties": {"name": {"allOf": [{"type": "string"}, {"not": {"const": ""}}]}},
        "required": ["name"],
    }
    consumer = {
        "type": "object",
        "properties": {"name": {"type": "string", "minLength": 1}},
        "required": ["name"],
    }
    result = api.check_subsumption(producer, consumer)
    print(
        f"   Producer excludes empty string, Consumer requires non-empty: {'✓ Compatible' if result.is_compatible else '✗ Incompatible'}"
    )

    # Example 2: Type exclusion conflict
    print("\n2. Type Exclusion Conflict:")
    producer = {
        "type": "object",
        "properties": {"value": {"not": {"type": "string"}}},
        "required": ["value"],
    }
    consumer = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }
    result = api.check_subsumption(producer, consumer)
    print(
        f"   Producer excludes strings, Consumer requires strings: {'✓ Compatible' if result.is_compatible else '✗ Incompatible'}"
    )

    # Example 3: Enum exclusion
    print("\n3. Enum Value Exclusion:")
    producer = {
        "type": "object",
        "properties": {"status": {"not": {"const": "error"}}},
        "required": ["status"],
    }
    consumer = {
        "type": "object",
        "properties": {"status": {"const": "success"}},
        "required": ["status"],
    }
    result = api.check_subsumption(producer, consumer)
    print(
        f"   Producer excludes 'error', Consumer requires 'success': {'✓ Compatible' if result.is_compatible else '✗ Incompatible'}"
    )

    print("\n" + "=" * 70)
