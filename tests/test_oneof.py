"""Tests for oneOf JSON Schema feature."""

import pytest
from src.jsound.api import JSoundAPI


class TestOneOf:
    """Test oneOf implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api = JSoundAPI(explanations=True)

    def test_compatible_identical_oneof(self):
        """Test compatible schemas with identical oneOf constraints."""
        schema = {"oneOf": [{"type": "string"}, {"type": "number"}]}

        result = self.api.check_subsumption(schema, schema)
        assert result.is_compatible

    def test_compatible_subset_oneof(self):
        """Test compatible oneOf where producer is subset of consumer."""
        producer = {"oneOf": [{"type": "string"}]}

        consumer = {"oneOf": [{"type": "string"}, {"type": "number"}]}

        result = self.api.check_subsumption(producer, consumer)
        assert result.is_compatible

    def test_incompatible_oneof_no_match(self):
        """Test incompatible oneOf where producer option has no consumer match."""
        producer = {"oneOf": [{"type": "string"}, {"type": "number"}]}

        consumer = {"oneOf": [{"type": "string"}, {"type": "integer"}]}

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.explanation is not None
        assert "matches producer oneOf option" in result.explanation
        assert "no consumer oneOf options" in result.explanation
        assert "oneOf:no_consumer_match" in str(result.failed_constraints)

    def test_incompatible_multiple_consumer_matches(self):
        """Test oneOf violation due to multiple matches in consumer."""
        producer = {"type": "integer"}

        consumer = {
            "oneOf": [
                {"type": "number"},  # integers are numbers
                {"type": "integer"},  # overlaps with previous
            ]
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.explanation is not None
        assert "multiple consumer oneOf options" in result.explanation
        assert "oneOf:multiple_matches" in str(result.failed_constraints)

    def test_oneof_with_constraints(self):
        """Test oneOf with additional constraints on options."""
        producer = {
            "oneOf": [
                {"type": "string", "minLength": 1},
                {"type": "number", "minimum": 0},
            ]
        }

        consumer = {
            "oneOf": [
                {"type": "string", "minLength": 5},
                {"type": "number", "minimum": 10},
            ]
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible

    def test_discriminated_union_pattern(self):
        """Test oneOf used for discriminated union pattern."""
        producer = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["success"]},
                        "data": {"type": "string"},
                    },
                    "required": ["type", "data"],
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["error"]},
                        "message": {"type": "string"},
                    },
                    "required": ["type", "message"],
                },
            ]
        }

        consumer = {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["success"]},
                        "data": {"type": "string"},
                    },
                    "required": ["type", "data"],
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["failure"],
                        },  # Different error type
                        "message": {"type": "string"},
                    },
                    "required": ["type", "message"],
                },
            ]
        }

        result = self.api.check_subsumption(producer, consumer)
        # Should be incompatible because error vs failure types don't match
        assert not result.is_compatible

    def test_oneof_vs_anyof_semantics(self):
        """Test that oneOf and anyOf have different semantics."""
        # Schema that would match multiple options
        value_schema = {"type": "integer", "minimum": 0}

        oneof_schema = {
            "oneOf": [
                {"type": "number"},  # integers are numbers
                {"type": "integer"},  # overlaps
            ]
        }

        anyof_schema = {
            "anyOf": [
                {"type": "number"},  # integers are numbers
                {"type": "integer"},  # overlaps - but anyOf allows this
            ]
        }

        # oneOf should reject overlapping matches
        oneof_result = self.api.check_subsumption(value_schema, oneof_schema)
        assert not oneof_result.is_compatible

        # anyOf should accept overlapping matches
        anyof_result = self.api.check_subsumption(value_schema, anyof_schema)
        assert anyof_result.is_compatible

    def test_oneof_recommendations(self):
        """Test that recommendations are provided for oneOf failures."""
        producer = {"oneOf": [{"type": "string"}, {"type": "number"}]}

        consumer = {"oneOf": [{"type": "string"}, {"type": "boolean"}]}

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.recommendations is not None
        assert len(result.recommendations) > 0

        # Check that recommendation mentions oneOf
        rec_text = " ".join(result.recommendations)
        assert "oneOf" in rec_text.lower() or "compatible" in rec_text.lower()

    def test_nested_oneof_in_objects(self):
        """Test oneOf constraints in object properties."""
        producer = {
            "type": "object",
            "properties": {
                "value": {"oneOf": [{"type": "string"}, {"type": "number"}]}
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "value": {"oneOf": [{"type": "string"}, {"type": "integer"}]}
            },
        }

        result = self.api.check_subsumption(producer, consumer)
        # Should be incompatible due to number vs integer mismatch
        assert not result.is_compatible

    def test_complex_oneof_scenario(self):
        """Test complex oneOf scenario with multiple constraint types."""
        producer = {
            "oneOf": [
                {"type": "string", "format": "email", "maxLength": 100},
                {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                    "required": ["id"],
                },
                {"type": "array", "items": {"type": "number"}, "maxItems": 5},
            ]
        }

        consumer = {
            "oneOf": [
                {
                    "type": "string",
                    "format": "uri",  # Different format
                    "maxLength": 100,
                },
                {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "name"],  # More restrictive
                },
                {
                    "type": "array",
                    "items": {"type": "integer"},  # More restrictive
                    "maxItems": 5,
                },
            ]
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.explanation is not None
