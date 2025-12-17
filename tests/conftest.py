"""
Shared pytest fixtures for JSO subsumption testing.
"""

import pytest
import sys
import os

# Add src and tests to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from jsound.api import JSoundAPI
from test_examples.schemas import (
    USER_PROFILE_STRICT,
    USER_PROFILE_LOOSE,
    ADDRESS_DETAILED,
    ADDRESS_MINIMAL,
    MOVIE_ACTION,
    MOVIE_GENERAL,
    LOCATION_PRECISE,
    LOCATION_GENERAL,
    PERSON_WITH_ADDRESS,
    PERSON_WITH_DETAILED_ADDRESS,
    TREE_NODE_SCHEMA,
    LINKED_LIST_SCHEMA,
    ECOMMERCE_SYSTEM,
    SUBSUMPTION_TEST_CASES,
    ANTI_SUBSUMPTION_TEST_CASES,
)


@pytest.fixture
def api():
    """Create JSoundAPI instance for testing."""
    return JSoundAPI(timeout=10)


@pytest.fixture
def basic_types():
    """Common basic type schemas."""
    return {
        "integer": {"type": "integer"},
        "number": {"type": "number"},
        "string": {"type": "string"},
        "boolean": {"type": "boolean"},
        "array": {"type": "array"},
        "object": {"type": "object"},
        "null": {"type": "null"},
    }


@pytest.fixture
def number_schemas():
    """Number type schemas with various constraints."""
    return {
        "integer": {"type": "integer"},
        "number": {"type": "number"},
        "positive_integer": {"type": "integer", "minimum": 1},
        "junior_salary": {"type": "number", "minimum": 40000, "maximum": 60000},
        "general_salary": {"type": "number", "minimum": 30000, "maximum": 200000},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
    }


@pytest.fixture
def string_schemas():
    """String type schemas with various constraints."""
    return {
        "string": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "short_string": {"type": "string", "minLength": 1, "maxLength": 10},
        "long_string": {"type": "string", "minLength": 5, "maxLength": 100},
        "username": {"type": "string", "pattern": "^[a-zA-Z0-9_]+$"},
        "const_hello": {"const": "hello"},
        "enum_colors": {"enum": ["red", "green", "blue"]},
        "enum_extended": {"enum": ["red", "green", "blue", "yellow", "orange"]},
    }


@pytest.fixture
def array_schemas():
    """Array type schemas with various constraints."""
    return {
        "string_array": {"type": "array", "items": {"type": "string"}},
        "number_array": {"type": "array", "items": {"type": "number"}},
        "short_array": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
        "long_array": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 0,
            "maxItems": 10,
        },
        "required_array": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 10,
        },
    }


@pytest.fixture
def object_schemas():
    """Object type schemas with various constraints."""
    return {
        "empty_object": {"type": "object"},
        "flexible_object": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": True,
        },
        "strict_object": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        },
        "required_name": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
        "required_name_email": {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
        },
    }


@pytest.fixture
def composition_schemas():
    """Schemas using anyOf, oneOf, allOf composition."""
    return {
        "string_or_number": {"anyOf": [{"type": "string"}, {"type": "number"}]},
        "string_or_integer": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        "string_number_boolean": {
            "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "boolean"}]
        },
        "strict_allof": {
            "allOf": [
                {"type": "object", "properties": {"value": {"type": "integer"}}},
                {
                    "type": "object",
                    "required": ["value", "name"],
                    "properties": {"name": {"type": "string"}},
                },
            ]
        },
        "simple_oneof": {"oneOf": [{"type": "string"}, {"type": "number"}]},
    }


@pytest.fixture
def real_world_schemas():
    """Real-world schema examples from JSON Schema website."""
    return {
        "user_strict": USER_PROFILE_STRICT,
        "user_loose": USER_PROFILE_LOOSE,
        "address_detailed": ADDRESS_DETAILED,
        "address_minimal": ADDRESS_MINIMAL,
        "movie_action": MOVIE_ACTION,
        "movie_general": MOVIE_GENERAL,
        "location_precise": LOCATION_PRECISE,
        "location_general": LOCATION_GENERAL,
    }


@pytest.fixture
def ref_schemas():
    """Schemas with $ref examples."""
    return {
        "person_with_address": PERSON_WITH_ADDRESS,
        "person_with_detailed_address": PERSON_WITH_DETAILED_ADDRESS,
        "tree_node": TREE_NODE_SCHEMA,
        "linked_list": LINKED_LIST_SCHEMA,
        "ecommerce": ECOMMERCE_SYSTEM,
    }


@pytest.fixture
def subsumption_test_cases():
    """Parametrized test cases for valid subsumption."""
    return SUBSUMPTION_TEST_CASES


@pytest.fixture
def anti_subsumption_test_cases():
    """Parametrized test cases for invalid subsumption."""
    return ANTI_SUBSUMPTION_TEST_CASES


@pytest.fixture
def nested_schemas():
    """Complex nested schema examples."""
    return {
        "nested_producer": {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "required": ["profile"],
                    "properties": {
                        "profile": {
                            "type": "object",
                            "required": ["name", "email"],
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        }
                    },
                }
            },
        },
        "nested_consumer": {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        }
                    },
                }
            },
        },
    }
