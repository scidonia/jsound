"""
Real-world JSON Schema examples for testing subsumption.
Based on examples from https://json-schema.org/learn/json-schema-examples
"""

# User Profile Schema Examples
USER_PROFILE_STRICT = {
    "type": "object",
    "required": ["username", "email", "fullName"],
    "properties": {
        "username": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "fullName": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
        "location": {"type": "string"},
        "interests": {"type": "array", "items": {"type": "string"}},
    },
}

USER_PROFILE_LOOSE = {
    "type": "object",
    "required": ["username"],
    "properties": {
        "username": {"type": "string"},
        "email": {"type": "string"},
        "fullName": {"type": "string"},
        "age": {"type": "integer"},
        "location": {"type": "string"},
        "interests": {"type": "array", "items": {"type": "string"}},
    },
}

# Address Schema Examples
ADDRESS_DETAILED = {
    "type": "object",
    "required": ["locality", "region", "countryName", "streetAddress"],
    "properties": {
        "postOfficeBox": {"type": "string"},
        "extendedAddress": {"type": "string"},
        "streetAddress": {"type": "string"},
        "locality": {"type": "string"},
        "region": {"type": "string"},
        "postalCode": {"type": "string"},
        "countryName": {"type": "string"},
    },
}

ADDRESS_MINIMAL = {
    "type": "object",
    "required": ["locality", "region", "countryName"],
    "properties": {
        "streetAddress": {"type": "string"},
        "locality": {"type": "string"},
        "region": {"type": "string"},
        "postalCode": {"type": "string"},
        "countryName": {"type": "string"},
    },
}

# Movie Schema Examples
MOVIE_ACTION = {
    "type": "object",
    "required": ["title", "director", "releaseDate"],
    "properties": {
        "title": {"type": "string"},
        "director": {"type": "string"},
        "releaseDate": {"type": "string", "format": "date"},
        "genre": {"const": "Action"},
        "duration": {"type": "string"},
        "cast": {"type": "array", "items": {"type": "string"}},
    },
}

MOVIE_GENERAL = {
    "type": "object",
    "required": ["title", "director", "releaseDate"],
    "properties": {
        "title": {"type": "string"},
        "director": {"type": "string"},
        "releaseDate": {"type": "string", "format": "date"},
        "genre": {
            "type": "string",
            "enum": ["Action", "Comedy", "Drama", "Science Fiction"],
        },
        "duration": {"type": "string"},
        "cast": {"type": "array", "items": {"type": "string"}},
    },
}

# Geographical Location Examples
LOCATION_PRECISE = {
    "type": "object",
    "required": ["latitude", "longitude"],
    "properties": {
        "latitude": {"type": "number", "minimum": 48.85, "maximum": 48.86},
        "longitude": {"type": "number", "minimum": 2.29, "maximum": 2.30},
    },
}

LOCATION_GENERAL = {
    "type": "object",
    "required": ["latitude", "longitude"],
    "properties": {
        "latitude": {"type": "number", "minimum": -90, "maximum": 90},
        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
    },
}

# Schemas with $ref (acyclic)
PERSON_WITH_ADDRESS = {
    "$defs": {
        "Address": ADDRESS_MINIMAL,
        "Person": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "address": {"$ref": "#/$defs/Address"},
            },
        },
    },
    "type": "object",
    "properties": {"person": {"$ref": "#/$defs/Person"}},
}

PERSON_WITH_DETAILED_ADDRESS = {
    "$defs": {
        "Address": ADDRESS_DETAILED,
        "Person": {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "address": {"$ref": "#/$defs/Address"},
            },
        },
    },
    "type": "object",
    "required": ["person"],
    "properties": {"person": {"$ref": "#/$defs/Person"}},
}

# Schemas with $ref (cyclic)
TREE_NODE_SCHEMA = {
    "$defs": {
        "Node": {
            "type": "object",
            "required": ["value"],
            "properties": {
                "value": {"type": "integer"},
                "children": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
            },
        }
    },
    "$ref": "#/$defs/Node",
}

LINKED_LIST_SCHEMA = {
    "$defs": {
        "Node": {
            "type": "object",
            "required": ["value"],
            "properties": {
                "value": {"type": "string"},
                "next": {"$ref": "#/$defs/Node"},
            },
        }
    },
    "$ref": "#/$defs/Node",
}

# Complex e-commerce example with $ref
ECOMMERCE_SYSTEM = {
    "$defs": {
        "Product": {
            "type": "object",
            "required": ["name", "price"],
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number", "minimum": 0},
                "category": {"type": "string"},
            },
        },
        "Order": {
            "type": "object",
            "required": ["orderId", "items"],
            "properties": {
                "orderId": {"type": "string"},
                "items": {"type": "array", "items": {"$ref": "#/$defs/Product"}},
                "total": {"type": "number", "minimum": 0},
            },
        },
    },
    "type": "object",
    "properties": {"orders": {"type": "array", "items": {"$ref": "#/$defs/Order"}}},
}

# Test cases for subsumption relationships
SUBSUMPTION_TEST_CASES = [
    # (producer, consumer, expected_result, description)
    ({"type": "integer"}, {"type": "number"}, True, "Integer subsumes number"),
    ({"type": "number"}, {"type": "integer"}, False, "Number does not subsume integer"),
    (
        {"type": "string", "minLength": 5},
        {"type": "string", "minLength": 3},
        True,
        "Stricter string constraint subsumes looser",
    ),
    (
        {"type": "array", "maxItems": 3},
        {"type": "array", "maxItems": 5},
        True,
        "Shorter array subsumes longer array",
    ),
    (
        {"type": "object", "required": ["a", "b"]},
        {"type": "object", "required": ["a"]},
        True,
        "More required fields subsumes fewer required fields",
    ),
    ({"const": "hello"}, {"type": "string"}, True, "Constant subsumes general type"),
    (
        {"enum": ["red", "blue"]},
        {"enum": ["red", "blue", "green"]},
        True,
        "Smaller enum subsumes larger enum",
    ),
    (
        USER_PROFILE_STRICT,
        USER_PROFILE_LOOSE,
        True,
        "Strict user profile subsumes loose",
    ),
    (
        USER_PROFILE_LOOSE,
        USER_PROFILE_STRICT,
        False,
        "Loose user profile does not subsume strict",
    ),
    (
        LOCATION_PRECISE,
        LOCATION_GENERAL,
        True,
        "Precise location subsumes general location",
    ),
    (MOVIE_ACTION, MOVIE_GENERAL, True, "Action movie subsumes general movie"),
]

# Anti-subsumption test cases (should return False)
ANTI_SUBSUMPTION_TEST_CASES = [
    ({"type": "string"}, {"type": "number"}, "Different types are incompatible"),
    (
        {"type": "array", "minItems": 5},
        {"type": "array", "maxItems": 3},
        "Array constraints conflict",
    ),
    ({"const": "hello"}, {"const": "world"}, "Different constants are incompatible"),
    (
        {"type": "object", "additionalProperties": True},
        {"type": "object", "additionalProperties": False},
        "Flexible object does not subsume strict object",
    ),
]
