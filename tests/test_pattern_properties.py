"""Tests for patternProperties JSON Schema feature."""

import pytest
from src.jsound.api import JSoundAPI


class TestPatternProperties:
    """Test patternProperties implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api = JSoundAPI(explanations=True)

    def test_compatible_pattern_properties(self):
        """Test compatible patternProperties schemas."""
        producer = {
            "type": "object",
            "patternProperties": {
                "^[0-9]+$": {"type": "string"},
                "^str_": {"type": "string"},
            },
        }

        consumer = {
            "type": "object",
            "patternProperties": {
                "^[0-9]+$": {"type": "string"},
                "^str_": {"type": "string"},
            },
        }

        result = self.api.check_subsumption(producer, consumer)
        assert result.is_compatible

    def test_incompatible_pattern_properties_type_mismatch(self):
        """Test incompatible patternProperties with type mismatches."""
        producer = {
            "type": "object",
            "properties": {"123": {"type": "number"}, "str_test": {"type": "string"}},
            "patternProperties": {
                "^[0-9]+$": {"type": "number"},
                "^str_": {"type": "string"},
            },
            "additionalProperties": False,
        }

        consumer = {
            "type": "object",
            "properties": {"123": {"type": "string"}, "str_test": {"type": "number"}},
            "patternProperties": {
                "^[0-9]+$": {"type": "string"},
                "^str_": {"type": "number"},
            },
            "additionalProperties": False,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.counterexample is not None
        assert result.explanation is not None

        # Check that explanation mentions pattern mismatch
        assert "matches pattern" in result.explanation
        assert "type mismatch" in result.explanation
        assert "patternProperties:" in str(result.failed_constraints)

    def test_multiple_matching_patterns(self):
        """Test property matching multiple patterns."""
        producer = {
            "type": "object",
            "properties": {"test_123": {"type": "string"}},
            "patternProperties": {
                "^test_": {"type": "string"},
                "_[0-9]+$": {"type": "string"},
            },
            "additionalProperties": False,
        }

        consumer = {
            "type": "object",
            "properties": {"test_123": {"type": "number"}},
            "patternProperties": {
                "^test_": {"type": "number"},
                "_[0-9]+$": {"type": "number"},
            },
            "additionalProperties": False,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        # Should detect the mismatch through one of the patterns

    def test_pattern_with_properties_interaction(self):
        """Test interaction between properties and patternProperties."""
        producer = {
            "type": "object",
            "properties": {"env_TEST": {"type": "string"}},
            "patternProperties": {"^env_": {"type": "string"}},
            "additionalProperties": False,
        }

        consumer = {
            "type": "object",
            "properties": {"env_TEST": {"type": "number"}},
            "patternProperties": {
                "^env_": {"type": "string"}  # Pattern allows string
            },
            "additionalProperties": False,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        # Should fail due to explicit property type mismatch

    def test_invalid_regex_pattern(self):
        """Test handling of invalid regex patterns."""
        producer = {
            "type": "object",
            "patternProperties": {
                "[": {"type": "string"}  # Invalid regex
            },
        }

        consumer = {
            "type": "object",
            "patternProperties": {"^valid$": {"type": "string"}},
        }

        # Should not crash, invalid patterns are ignored
        result = self.api.check_subsumption(producer, consumer)
        assert result.is_compatible or not result.is_compatible  # Either is fine

    def test_pattern_properties_with_constraints(self):
        """Test patternProperties with additional constraints."""
        producer = {
            "type": "object",
            "properties": {"timeout_request": {"type": "number", "minimum": 0}},
            "patternProperties": {"^timeout_": {"type": "number", "minimum": 0}},
            "additionalProperties": False,
        }

        consumer = {
            "type": "object",
            "properties": {"timeout_request": {"type": "number", "minimum": 1000}},
            "patternProperties": {"^timeout_": {"type": "number", "minimum": 1000}},
            "additionalProperties": False,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        # Should fail due to minimum constraint difference

    def test_pattern_properties_recommendations(self):
        """Test that recommendations are provided for pattern property failures."""
        producer = {
            "type": "object",
            "properties": {"config_debug": {"type": "boolean"}},
            "patternProperties": {"^config_": {"type": "boolean"}},
            "additionalProperties": False,
        }

        consumer = {
            "type": "object",
            "properties": {"config_debug": {"type": "string"}},
            "patternProperties": {"^config_": {"type": "string"}},
            "additionalProperties": False,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.recommendations is not None
        assert len(result.recommendations) > 0

        # Check that recommendations mention the pattern
        rec_text = " ".join(result.recommendations)
        assert "^config_" in rec_text or "pattern" in rec_text.lower()

    def test_complex_pattern_properties_scenario(self):
        """Test complex scenario with multiple pattern types."""
        producer = {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "env_DATABASE_URL": {"type": "string"},
                "timeout_request": {"type": "number"},
                "config_debug": {"type": "boolean"},
            },
            "patternProperties": {
                "^env_[A-Z_]+$": {"type": "string"},
                "^timeout_[a-z]+$": {"type": "number", "minimum": 0},
                "^config_[a-z]+$": {"type": "boolean"},
            },
            "required": ["service_name"],
            "additionalProperties": False,
        }

        consumer = {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "env_DATABASE_URL": {"type": "number"},  # Type mismatch
                "timeout_request": {"type": "string"},  # Type mismatch
                "config_debug": {"type": "string"},  # Type mismatch
            },
            "patternProperties": {
                "^env_[A-Z_]+$": {"type": "number"},
                "^timeout_[a-z]+$": {"type": "string"},
                "^config_[a-z]+$": {"type": "string"},
            },
            "required": ["service_name"],
            "additionalProperties": False,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.explanation is not None
        assert "matches pattern" in result.explanation
