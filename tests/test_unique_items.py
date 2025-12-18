"""Tests for uniqueItems JSON Schema feature."""

import pytest
from src.jsound.api import JSoundAPI


class TestUniqueItems:
    """Test uniqueItems implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api = JSoundAPI(explanations=True)

    def test_compatible_unique_items_same_constraint(self):
        """Test compatible schemas with same uniqueItems constraint."""
        producer = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}

        consumer = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}

        result = self.api.check_subsumption(producer, consumer)
        assert result.is_compatible

    def test_compatible_unique_producer_to_non_unique_consumer(self):
        """Test compatible: unique producer to non-unique consumer."""
        producer = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}

        consumer = {"type": "array", "items": {"type": "string"}, "uniqueItems": False}

        result = self.api.check_subsumption(producer, consumer)
        assert result.is_compatible

    def test_incompatible_non_unique_to_unique(self):
        """Test incompatible: non-unique producer to unique consumer."""
        producer = {"type": "array", "items": {"type": "string"}, "uniqueItems": False}

        consumer = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.counterexample is not None
        assert result.explanation is not None

        # Check that explanation mentions duplicates
        assert "duplicate elements" in result.explanation
        assert "indices" in result.explanation
        assert "uniqueItems:true" in str(result.failed_constraints)

    def test_unique_items_with_different_types(self):
        """Test uniqueItems with different item types."""
        producer = {"type": "array", "items": {"type": "number"}, "uniqueItems": False}

        consumer = {"type": "array", "items": {"type": "number"}, "uniqueItems": True}

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible

    def test_unique_items_in_object_properties(self):
        """Test uniqueItems constraint in object properties."""
        producer = {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        }

        consumer = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                }
            },
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.explanation is not None
        assert "tags" in result.explanation
        assert "duplicate elements" in result.explanation

    def test_multiple_array_properties_with_unique_items(self):
        """Test multiple array properties with uniqueItems constraints."""
        producer = {
            "type": "object",
            "properties": {
                "roles": {"type": "array", "items": {"type": "string"}},
                "permissions": {"type": "array", "items": {"type": "string"}},
            },
        }

        consumer = {
            "type": "object",
            "properties": {
                "roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
                "permissions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True,
                },
            },
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.explanation is not None
        # Should mention at least one of the properties with duplicates
        assert ("roles" in result.explanation) or ("permissions" in result.explanation)

    def test_unique_items_with_other_constraints(self):
        """Test uniqueItems combined with other array constraints."""
        producer = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 10,
        }

        consumer = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 10,
            "uniqueItems": True,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible

    def test_unique_items_recommendations(self):
        """Test that recommendations are provided for uniqueItems failures."""
        producer = {"type": "array", "items": {"type": "string"}}

        consumer = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}

        result = self.api.check_subsumption(producer, consumer)
        assert not result.is_compatible
        assert result.recommendations is not None
        assert len(result.recommendations) > 0

        # Check that recommendation mentions uniqueItems
        rec_text = " ".join(result.recommendations)
        assert "uniqueItems" in rec_text.lower()

    def test_unique_items_with_complex_items(self):
        """Test uniqueItems with complex item schemas."""
        producer = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
            },
        }

        consumer = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
            },
            "uniqueItems": True,
        }

        result = self.api.check_subsumption(producer, consumer)
        # This should be incompatible because producer allows duplicate objects
        assert not result.is_compatible

    def test_empty_arrays_with_unique_items(self):
        """Test that empty arrays satisfy uniqueItems constraint."""
        # This is more of a conceptual test - empty arrays should always
        # be compatible regardless of uniqueItems constraint
        producer = {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 0,  # Forces empty array
        }

        consumer = {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 0,  # Forces empty array
            "uniqueItems": True,
        }

        result = self.api.check_subsumption(producer, consumer)
        assert result.is_compatible  # Empty arrays have no duplicates
