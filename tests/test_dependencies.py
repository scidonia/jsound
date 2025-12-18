#!/usr/bin/env python3

import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jsound.api import JSoundAPI


class TestDependencies:
    """Test suite for JSON Schema dependencies feature."""

    def test_dependent_required_basic(self):
        """Test basic dependentRequired constraint."""
        producer = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
        }

        consumer = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "dependentRequired": {"name": ["email"]},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert result.counterexample is not None
        assert "name" in result.counterexample
        assert "email" not in result.counterexample
        assert (
            "Property 'name' requires 'email' but they are missing"
            in result.explanation
        )
        assert "dependentRequired:name→email" in result.failed_constraints
        assert (
            "Add properties 'email' to producer schema when 'name' is present"
            in result.recommendations
        )

    def test_dependent_required_multiple_deps(self):
        """Test dependentRequired with multiple dependencies."""
        producer = {
            "type": "object",
            "properties": {
                "credit_card": {"type": "string"},
                "billing_address": {"type": "string"},
                "cvv": {"type": "string"},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "credit_card": {"type": "string"},
                "billing_address": {"type": "string"},
                "cvv": {"type": "string"},
            },
            "dependentRequired": {"credit_card": ["billing_address", "cvv"]},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert "Property 'credit_card' requires" in result.explanation
        assert "billing_address" in result.explanation or "cvv" in result.explanation

    def test_legacy_dependencies_property_list(self):
        """Test legacy dependencies with property list (Draft 7)."""
        producer = {
            "type": "object",
            "properties": {
                "billing": {"type": "boolean"},
                "address": {"type": "string"},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "billing": {"type": "boolean"},
                "address": {"type": "string"},
            },
            "dependencies": {"billing": ["address"]},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert (
            "Property 'billing' requires 'address' but they are missing"
            in result.explanation
        )
        assert "dependencies:billing→address" in result.failed_constraints

    def test_legacy_dependencies_schema_object(self):
        """Test legacy dependencies with schema object (Draft 7)."""
        producer = {
            "type": "object",
            "properties": {"ssl": {"type": "boolean"}, "port": {"type": "integer"}},
        }

        consumer = {
            "type": "object",
            "properties": {"ssl": {"type": "boolean"}, "port": {"type": "integer"}},
            "dependencies": {"ssl": {"required": ["port"]}},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert (
            "Property 'ssl' requires object to satisfy dependency schema"
            in result.explanation
        )
        assert "dependencies:ssl" in result.failed_constraints

    def test_dependent_schemas_basic(self):
        """Test basic dependentSchemas constraint."""
        producer = {
            "type": "object",
            "properties": {
                "encryption": {"type": "boolean"},
                "key_size": {"type": "integer"},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "encryption": {"type": "boolean"},
                "key_size": {"type": "integer"},
            },
            "dependentSchemas": {"encryption": {"required": ["key_size"]}},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        assert (
            "Property 'encryption' requires object to satisfy schema"
            in result.explanation
        )
        assert "dependentSchemas:encryption" in result.failed_constraints

    def test_dependencies_compatible(self):
        """Test when dependencies are satisfied (should be compatible)."""
        producer = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name", "email"],
        }

        consumer = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "dependentRequired": {"name": ["email"]},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        # Should be compatible since producer always requires email when name exists
        assert result.is_compatible
        assert result.counterexample is None

    def test_dependencies_no_trigger_property(self):
        """Test when trigger property is not present (should be compatible)."""
        producer = {"type": "object", "properties": {"other": {"type": "string"}}}

        consumer = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "other": {"type": "string"},
            },
            "dependentRequired": {"name": ["email"]},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        # Should be compatible since "name" is not in producer
        assert result.is_compatible

    def test_multiple_dependencies_mixed(self):
        """Test multiple dependency types together."""
        producer = {
            "type": "object",
            "properties": {
                "auth": {"type": "string"},
                "ssl": {"type": "boolean"},
                "username": {"type": "string"},
                "cert": {"type": "string"},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "auth": {"type": "string"},
                "ssl": {"type": "boolean"},
                "username": {"type": "string"},
                "password": {"type": "string"},
                "cert": {"type": "string"},
            },
            "dependentRequired": {"auth": ["username"]},
            "dependencies": {"ssl": ["cert"]},
        }

        api = JSoundAPI()
        result = api.check_subsumption(producer, consumer)

        assert not result.is_compatible
        # Could fail on either dependency violation
        assert "auth" in result.explanation or "ssl" in result.explanation


if __name__ == "__main__":
    pytest.main([__file__])
