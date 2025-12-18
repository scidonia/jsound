#!/usr/bin/env python3

import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jsound.api import JSoundAPI


class TestConstEnumEnhanced:
    """Test suite for enhanced const/enum constraint explanations."""

    def test_const_mismatch(self):
        """Test const constraint mismatch with enhanced explanations."""
        producer = {"type": "string", "const": "active"}

        consumer = {"type": "string", "const": "enabled"}

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert result.counterexample is not None
        assert "const mismatch" in result.explanation
        assert "const:root:active→enabled" in result.failed_constraints
        assert (
            "Change schema const from 'active' to 'enabled'" in result.recommendations
        )

    def test_enum_subset_incompatible(self):
        """Test enum where producer allows values not in consumer enum."""
        producer = {"type": "string", "enum": ["low", "medium", "high", "critical"]}

        consumer = {"type": "string", "enum": ["low", "medium", "high"]}

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert result.counterexample is not None
        assert "enum mismatch" in result.explanation
        assert "critical" in result.explanation
        assert "enum_mismatch:root" in result.failed_constraints
        assert "Remove ['critical']" in result.recommendations

    def test_enum_subset_compatible(self):
        """Test enum where producer is subset of consumer (should be compatible)."""
        producer = {"type": "string", "enum": ["small", "medium"]}

        consumer = {"type": "string", "enum": ["small", "medium", "large"]}

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert result.is_compatible
        assert result.counterexample is None

    def test_const_vs_enum_incompatible(self):
        """Test const value not in consumer enum."""
        producer = {"type": "string", "const": "staging"}

        consumer = {"type": "string", "enum": ["development", "production"]}

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "const/enum mismatch" in result.explanation
        assert "staging" in result.explanation
        assert "const_enum_mismatch:root" in result.failed_constraints
        assert "Change schema const 'staging' to one of" in result.recommendations

    def test_enum_vs_const_incompatible(self):
        """Test enum allowing values outside consumer const."""
        producer = {"type": "string", "enum": ["active", "inactive", "pending"]}

        consumer = {"type": "string", "const": "active"}

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "const/enum mismatch" in result.explanation
        assert "const_enum_mismatch:root" in result.failed_constraints

    def test_property_const_mismatch(self):
        """Test const mismatch in object properties."""
        producer = {
            "type": "object",
            "properties": {"status": {"const": "active"}, "level": {"const": 1}},
        }

        consumer = {
            "type": "object",
            "properties": {
                "status": {"const": "enabled"},
                "level": {"const": 1},  # This should match
            },
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "Property 'status' const mismatch" in result.explanation
        assert "const:status:active→enabled" in result.failed_constraints
        assert (
            "Change property 'status' const from 'active' to 'enabled'"
            in result.recommendations
        )

    def test_property_enum_mismatch(self):
        """Test enum mismatch in object properties."""
        producer = {
            "type": "object",
            "properties": {
                "priority": {"enum": ["low", "medium", "high", "critical"]},
                "type": {"enum": ["bug", "feature"]},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "priority": {"enum": ["low", "medium", "high"]},
                "type": {"enum": ["bug", "feature"]},  # This should match
            },
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "Property 'priority' enum mismatch" in result.explanation
        assert "critical" in result.explanation
        assert "enum_mismatch:priority" in result.failed_constraints

    def test_const_violation_explanation(self):
        """Test explanation when value violates const constraint."""
        producer = {
            "type": "object",
            "properties": {
                "mode": {"type": "string"}  # Allows any string
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "mode": {"const": "production"}  # Requires specific value
            },
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "violates const constraint" in result.explanation
        assert "const_violation:mode" in result.failed_constraints
        assert (
            "Add property 'mode' const constraint 'production' to producer"
            in result.recommendations
        )

    def test_enum_violation_explanation(self):
        """Test explanation when value violates enum constraint."""
        producer = {
            "type": "object",
            "properties": {
                "size": {"type": "string"}  # Allows any string
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "size": {
                    "enum": ["small", "medium", "large"]
                }  # Requires specific values
            },
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "violates enum constraint" in result.explanation
        assert "enum_violation:size" in result.failed_constraints
        assert "Add property 'size' enum constraint" in result.recommendations

    def test_const_compatible(self):
        """Test when const constraints are identical (should be compatible)."""
        producer = {"type": "object", "properties": {"version": {"const": "1.0.0"}}}

        consumer = {"type": "object", "properties": {"version": {"const": "1.0.0"}}}

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert result.is_compatible
        assert result.counterexample is None

    def test_const_enum_compatible(self):
        """Test when const is in consumer enum (should be compatible)."""
        producer = {"type": "object", "properties": {"priority": {"const": "high"}}}

        consumer = {
            "type": "object",
            "properties": {"priority": {"enum": ["low", "medium", "high", "critical"]}},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert result.is_compatible
        assert result.counterexample is None


if __name__ == "__main__":
    pytest.main([__file__])
