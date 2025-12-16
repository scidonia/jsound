"""Bounds and finite universe management."""

from typing import Dict, List, Set, Any


class BoundsConfig:
    """Configuration for finite bounds and universes."""

    def __init__(
        self,
        max_array_len: int = 50,
        max_recursion_depth: int = 3,
        max_string_len: int = 100,
    ):
        self.max_array_len = max_array_len
        self.max_recursion_depth = max_recursion_depth
        self.max_string_len = max_string_len


class UniverseExtractor:
    """Extracts finite universes from schemas."""

    def extract_key_universe(self, *schemas: Dict[str, Any]) -> Set[str]:
        """Extract all object property names from schemas."""
        keys = set()
        for schema in schemas:
            self._extract_keys_recursive(schema, keys)
        return keys

    def _extract_keys_recursive(
        self, schema: Any, keys: Set[str], depth: int = 0
    ) -> None:
        """Recursively extract keys from schema."""
        if depth > 10:  # Prevent infinite recursion
            return

        if not isinstance(schema, dict):
            return

        # Extract from properties
        if "properties" in schema:
            keys.update(schema["properties"].keys())

        # Extract from patternProperties
        if "patternProperties" in schema:
            keys.update(schema["patternProperties"].keys())

        # Recursively process nested schemas
        for key, value in schema.items():
            if key in ["allOf", "anyOf", "oneOf"]:
                if isinstance(value, list):
                    for subschema in value:
                        self._extract_keys_recursive(subschema, keys, depth + 1)
            elif key in ["not", "items", "additionalProperties"]:
                self._extract_keys_recursive(value, keys, depth + 1)
            elif key in ["then", "else"]:
                self._extract_keys_recursive(value, keys, depth + 1)

    def extract_enum_values(self, *schemas: Dict[str, Any]) -> Set[Any]:
        """Extract all enum values from schemas."""
        values = set()
        for schema in schemas:
            self._extract_enum_values_recursive(schema, values)
        return values

    def _extract_enum_values_recursive(
        self, schema: Any, values: Set[Any], depth: int = 0
    ) -> None:
        """Recursively extract enum values from schema."""
        if depth > 10 or not isinstance(schema, dict):
            return

        if "enum" in schema:
            values.update(schema["enum"])

        if "const" in schema:
            values.add(schema["const"])

        # Recursively process nested schemas
        for key, value in schema.items():
            if key in ["allOf", "anyOf", "oneOf"]:
                if isinstance(value, list):
                    for subschema in value:
                        self._extract_enum_values_recursive(
                            subschema, values, depth + 1
                        )
            elif key in ["not", "items", "additionalProperties", "then", "else"]:
                self._extract_enum_values_recursive(value, values, depth + 1)
