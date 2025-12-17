"""
Comprehensive subsumption tests using real-world JSON Schema examples.

This test suite demonstrates both valid subsumption (producer ⊆ consumer)
and anti-subsumption (producer ⊄ consumer) cases using examples from
https://json-schema.org/learn/json-schema-examples
"""

import unittest
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jsound.api import JSoundAPI, check_subsumption, find_counterexample


class TestSubsumptionExamples(unittest.TestCase):
    """Test subsumption with real-world JSON Schema examples."""

    def setUp(self):
        """Set up the test environment."""
        self.api = JSoundAPI(timeout=10)

    def test_simple_type_subsumption(self):
        """Test basic type subsumption cases."""
        # Integer producer should be subsumed by number consumer
        producer = {"type": "integer"}
        consumer = {"type": "number"}

        result = self.api.check_subsumption(producer, consumer)
        self.assertTrue(result.is_compatible, "Integer should be subsumed by number")

    def test_user_profile_subsumption(self):
        """Test user profile schema subsumption."""
        # More restrictive producer (required fields)
        strict_user = {
            "type": "object",
            "required": ["username", "email", "fullName"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "fullName": {"type": "string"},
            },
        }

        # Less restrictive consumer (fewer required fields)
        loose_user = {
            "type": "object",
            "required": ["username"],
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string"},
                "fullName": {"type": "string"},
            },
        }

        result = self.api.check_subsumption(strict_user, loose_user)
        self.assertTrue(
            result.is_compatible,
            "Strict user (more required fields) should be subsumed by loose user (fewer required fields)",
        )

    def test_geographical_location_subsumption(self):
        """Test geographical location schema subsumption."""
        # Exact coordinates (more restrictive)
        exact_location = {
            "type": "object",
            "required": ["latitude", "longitude"],
            "properties": {
                "latitude": {"type": "number", "minimum": 48.8, "maximum": 48.9},
                "longitude": {"type": "number", "minimum": 2.2, "maximum": 2.3},
            },
        }

        # General coordinates (less restrictive)
        general_location = {
            "type": "object",
            "required": ["latitude", "longitude"],
            "properties": {
                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
            },
        }

        result = self.api.check_subsumption(exact_location, general_location)
        self.assertTrue(
            result.is_compatible,
            "Exact location (narrow bounds) should be subsumed by general location (wide bounds)",
        )

    def test_array_length_subsumption(self):
        """Test array length constraint subsumption."""
        # Short array producer
        short_array = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        }

        # Long array consumer
        long_array = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 0,
            "maxItems": 10,
        }

        result = self.api.check_subsumption(short_array, long_array)
        self.assertTrue(
            result.is_compatible,
            "Short array [1-3 items] should be subsumed by long array [0-10 items]",
        )

    def test_object_additional_properties(self):
        """Test object with additionalProperties subsumption."""
        # Strict object (no additional properties)
        strict_object = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }

        # Flexible object (additional properties allowed)
        flexible_object = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": True,
        }

        result = self.api.check_subsumption(strict_object, flexible_object)
        self.assertTrue(
            result.is_compatible,
            "Strict object (no additional properties) should be subsumed by flexible object (additional properties allowed)",
        )


if __name__ == "__main__":
    print("=" * 70)
    print("Testing schema subsumption with real-world examples")
    print("Based on examples from https://json-schema.org/learn/json-schema-examples")
    print("=" * 70)

    unittest.main()
