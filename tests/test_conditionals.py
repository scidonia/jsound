"""Tests for if/then/else conditional schema constraints."""

import pytest
from jsound.core.subsumption import SubsumptionChecker, SolverConfig


class TestConditionalConstraints:
    """Test if/then/else conditional constraints."""

    @pytest.fixture
    def checker(self):
        """Create a subsumption checker."""
        config = SolverConfig(timeout=10)
        return SubsumptionChecker(config)

    @pytest.mark.subsumption
    def test_simple_if_then_subsumption(self, checker):
        """Test basic if/then conditional subsumption."""
        producer = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0},
                "name": {"type": "string"},
            },
            "if": {"properties": {"age": {"minimum": 18}}},
            "then": {"properties": {"name": {"pattern": "^[A-Z]"}}},
        }

        consumer = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0},
                "name": {"type": "string"},
            },
            "if": {"properties": {"age": {"minimum": 18}}},
            "then": {"properties": {"name": {"minLength": 1}}},
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with stricter then-clause should subsume consumer with looser then-clause"
        )

    @pytest.mark.subsumption
    def test_if_then_else_subsumption(self, checker):
        """Test if/then/else conditional subsumption."""
        producer = {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["premium", "basic"]},
                "price": {"type": "number", "minimum": 0},
            },
            "required": ["type", "price"],
            "if": {"properties": {"type": {"const": "premium"}}},
            "then": {"properties": {"price": {"minimum": 100}}},
            "else": {"properties": {"price": {"maximum": 50}}},
        }

        consumer = {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["premium", "basic", "enterprise"]},
                "price": {"type": "number", "minimum": 0},
            },
            "required": ["type", "price"],
            "if": {"properties": {"type": {"const": "premium"}}},
            "then": {"properties": {"price": {"minimum": 50}}},
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with stricter price constraints should subsume consumer with looser constraints"
        )

    @pytest.mark.anti_subsumption
    def test_conflicting_conditionals_anti_subsumption(self, checker):
        """Test that conflicting conditionals are incompatible."""
        producer = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0},
                "name": {"type": "string"},
            },
            "if": {"properties": {"age": {"minimum": 18}}},
            "then": {
                "properties": {"name": {"pattern": "^[a-z]"}}  # lowercase
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0},
                "name": {"type": "string"},
            },
            "if": {"properties": {"age": {"minimum": 18}}},
            "then": {
                "properties": {
                    "name": {"pattern": "^[A-Z]"}
                }  # uppercase - conflicting!
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert not result.is_compatible, (
            "Conflicting pattern constraints should be incompatible"
        )
        assert result.counterexample is not None, (
            "Should provide counterexample for conflicting patterns"
        )

    @pytest.mark.subsumption
    def test_if_without_then_else(self, checker):
        """Test if constraint without then/else clauses."""
        producer = {
            "type": "object",
            "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 100}},
            "if": {"properties": {"score": {"minimum": 90}}},
        }

        consumer = {
            "type": "object",
            "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 100}},
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Schema with additional if constraint should subsume schema without it"
        )

    @pytest.mark.subsumption
    def test_then_without_if(self, checker):
        """Test then constraint without if clause (should always apply)."""
        producer = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "then": {"properties": {"name": {"minLength": 5}}},
        }

        consumer = {
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 3}},
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Always-applied then constraint (minLength 5) should subsume looser constraint (minLength 3)"
        )

    @pytest.mark.subsumption
    def test_complex_nested_conditionals(self, checker):
        """Test complex conditional with nested object properties."""
        producer = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["admin", "user"]},
                        "permissions": {"type": "array", "items": {"type": "string"}},
                    },
                }
            },
            "if": {
                "properties": {"user": {"properties": {"role": {"const": "admin"}}}}
            },
            "then": {
                "properties": {"user": {"properties": {"permissions": {"minItems": 5}}}}
            },
            "else": {
                "properties": {"user": {"properties": {"permissions": {"maxItems": 3}}}}
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["admin", "user", "guest"]},
                        "permissions": {"type": "array", "items": {"type": "string"}},
                    },
                }
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with role-based permission constraints should subsume unconstrained consumer"
        )

    @pytest.mark.subsumption
    def test_conditional_self_subsumption(self, checker):
        """Test that conditional schemas subsume themselves."""
        schema = {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["A", "B", "C"]},
                "value": {"type": "number"},
            },
            "if": {"properties": {"category": {"const": "A"}}},
            "then": {"properties": {"value": {"minimum": 100}}},
            "else": {"properties": {"value": {"maximum": 50}}},
        }

        result = checker.check_subsumption(schema, schema)
        assert result.is_compatible, "Any schema should subsume itself"


class TestConditionalEdgeCases:
    """Test edge cases and complex scenarios for conditional constraints."""

    @pytest.fixture
    def checker(self):
        config = SolverConfig(timeout=10)
        return SubsumptionChecker(config)

    @pytest.mark.subsumption
    def test_multiple_conditions_same_result(self, checker):
        """Test multiple if conditions leading to same then result."""
        producer = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "pending", "inactive"]},
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            },
            "allOf": [
                {
                    "if": {"properties": {"status": {"const": "active"}}},
                    "then": {"properties": {"priority": {"minimum": 3}}},
                },
                {
                    "if": {"properties": {"status": {"const": "pending"}}},
                    "then": {"properties": {"priority": {"minimum": 3}}},
                },
            ],
        }

        consumer = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "pending", "inactive"]},
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            },
        }

        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Producer with conditional priority constraints should subsume unconstrained consumer"
        )

    @pytest.mark.anti_subsumption
    def test_impossible_condition_combination(self, checker):
        """Test impossible condition combinations."""
        producer = {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 0, "maximum": 100}},
            "if": {
                "properties": {
                    "value": {"minimum": 50, "maximum": 40}
                }  # impossible: min > max
            },
            "then": {"properties": {"value": {"multipleOf": 7}}},
        }

        consumer = {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 0, "maximum": 100}},
        }

        # This should still be compatible since the if condition is never true
        result = checker.check_subsumption(producer, consumer)
        assert result.is_compatible, (
            "Impossible if condition should not affect compatibility"
        )
