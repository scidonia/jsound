"""JSON Schema to Z3 predicate compilation."""

from typing import Any, Dict, List, Set, Optional
from z3 import *
from ..exceptions import UnsupportedFeatureError


class SchemaCompiler:
    """Compiles JSON schemas to Z3 predicates."""

    def __init__(self, json_encoder, key_universe):
        self.json_encoder = json_encoder
        self.key_universe = key_universe
        self._current_depth = 0
        self.max_recursion_depth = 3

    def compile_schema(self, schema: Dict[str, Any], json_var):
        """Compile a JSON schema to a Z3 predicate."""
        if self._current_depth > self.max_recursion_depth:
            raise UnsupportedFeatureError(
                f"Schema nesting too deep (>{self.max_recursion_depth})"
            )

        self._current_depth += 1

        try:
            constraints = []

            # Handle type constraints
            if "type" in schema:
                constraints.append(
                    self.compile_type_constraint(json_var, schema["type"])
                )

            # Handle const/enum
            if "const" in schema:
                constraints.append(
                    self.compile_const_constraint(json_var, schema["const"])
                )
            elif "enum" in schema:
                constraints.append(
                    self.compile_enum_constraint(json_var, schema["enum"])
                )

            # Handle boolean composition
            if "allOf" in schema:
                constraints.append(self.compile_all_of(json_var, schema["allOf"]))
            if "anyOf" in schema:
                constraints.append(self.compile_any_of(json_var, schema["anyOf"]))
            if "oneOf" in schema:
                constraints.append(self.compile_one_of(json_var, schema["oneOf"]))
            if "not" in schema:
                constraints.append(self.compile_not(json_var, schema["not"]))

            # Handle string constraints
            if any(k in schema for k in ["minLength", "maxLength", "pattern"]):
                constraints.append(self.compile_string_constraints(json_var, schema))

            # Combine all constraints
            if not constraints:
                return BoolVal(True)  # Empty schema accepts everything
            elif len(constraints) == 1:
                return constraints[0]
            else:
                return And(*constraints)

        finally:
            self._current_depth -= 1

    def compile_type_constraint(self, json_var, type_spec):
        """Compile type constraints."""
        predicates = self.json_encoder.create_type_predicates()

        if isinstance(type_spec, str):
            # Single type
            if type_spec == "null":
                return predicates["is_null"](json_var)
            elif type_spec == "boolean":
                return predicates["is_bool"](json_var)
            elif type_spec == "integer":
                return predicates["is_int"](json_var)
            elif type_spec == "number":
                return Or(
                    predicates["is_int"](json_var), predicates["is_real"](json_var)
                )
            elif type_spec == "string":
                return predicates["is_str"](json_var)
            elif type_spec == "array":
                return predicates["is_arr"](json_var)
            elif type_spec == "object":
                return predicates["is_obj"](json_var)
            else:
                raise UnsupportedFeatureError(f"Unsupported type: {type_spec}")

        elif isinstance(type_spec, list):
            # Array of types - any of them can match
            type_constraints = []
            for t in type_spec:
                type_constraints.append(self.compile_type_constraint(json_var, t))
            return Or(*type_constraints)

        else:
            raise UnsupportedFeatureError(f"Invalid type specification: {type_spec}")

    def compile_const_constraint(self, json_var, const_value):
        """Compile const constraints."""
        encoded_value = self.json_encoder.encode_python_value(const_value)
        return json_var == encoded_value

    def compile_enum_constraint(self, json_var, enum_values):
        """Compile enum constraints."""
        constraints = []
        for value in enum_values:
            encoded_value = self.json_encoder.encode_python_value(value)
            constraints.append(json_var == encoded_value)
        return Or(*constraints)

    def compile_all_of(self, json_var, schemas):
        """Compile allOf - all schemas must match."""
        constraints = []
        for schema in schemas:
            constraints.append(self.compile_schema(schema, json_var))
        return And(*constraints)

    def compile_any_of(self, json_var, schemas):
        """Compile anyOf - at least one schema must match."""
        constraints = []
        for schema in schemas:
            constraints.append(self.compile_schema(schema, json_var))
        return Or(*constraints)

    def compile_one_of(self, json_var, schemas):
        """Compile oneOf - exactly one schema must match."""
        constraints = []
        for schema in schemas:
            constraints.append(self.compile_schema(schema, json_var))
        # Exactly one should be true
        return PbEq([(c, 1) for c in constraints], 1)

    def compile_not(self, json_var, schema):
        """Compile not - schema must not match."""
        return Not(self.compile_schema(schema, json_var))

    def compile_string_constraints(self, json_var, schema):
        """Compile string-specific constraints."""
        predicates = self.json_encoder.create_type_predicates()
        accessors = self.json_encoder.get_accessors()

        # First, ensure it's a string
        constraints = [predicates["is_str"](json_var)]

        # Get the string value
        str_val = accessors["str_val"](json_var)

        # Handle string length constraints
        if "minLength" in schema:
            constraints.append(Length(str_val) >= IntVal(schema["minLength"]))
        if "maxLength" in schema:
            constraints.append(Length(str_val) <= IntVal(schema["maxLength"]))

        # Handle pattern constraint
        if "pattern" in schema:
            pattern = schema["pattern"]
            try:
                # Convert JSON Schema regex to Z3 regex
                z3_regex = self._convert_regex_pattern(pattern)
                constraints.append(InRe(str_val, z3_regex))
            except Exception as e:
                raise UnsupportedFeatureError(
                    f"Regex pattern '{pattern}' not supported: {e}"
                )

        return And(*constraints)

    def _convert_regex_pattern(self, pattern):
        """Convert JSON Schema regex pattern to Z3 regex."""

        # For now, support only basic patterns
        # This is a simplified implementation - full regex support would be much more complex

        if pattern == "^[0-9]+$":
            # Only digits, one or more
            return Re("[0-9]+")
        elif pattern == "^[a-zA-Z]+$":
            # Only letters, one or more
            return Re("[a-zA-Z]+")
        elif pattern == "^[a-zA-Z0-9]+$":
            # Letters and digits, one or more
            return Re("[a-zA-Z0-9]+")
        elif pattern.startswith("^") and pattern.endswith("$"):
            # Strip anchors and try basic conversion
            inner_pattern = pattern[1:-1]
            try:
                return Re(inner_pattern)
            except:
                raise UnsupportedFeatureError(
                    f"Complex regex pattern not supported: {pattern}"
                )
        else:
            # Try direct conversion for simple patterns
            try:
                return Re(pattern)
            except:
                raise UnsupportedFeatureError(f"Regex pattern not supported: {pattern}")

    def _simple_regex_to_z3(self, pattern):
        """Convert simple regex patterns to Z3."""
        # This would need much more sophisticated regex parsing
        # For now, just support the most basic cases
        return Re(pattern)


class ObjectConstraintBuilder:
    """Handles object-specific constraint building."""

    def build_property_constraints(self, json_var, properties):
        """Build constraints for object properties."""
        # TODO: Implement property constraints
        return BoolVal(True)

    def build_required_constraints(self, json_var, required):
        """Build constraints for required properties."""
        # TODO: Implement required constraints
        return BoolVal(True)


class ArrayConstraintBuilder:
    """Handles array-specific constraint building."""

    def build_items_constraints(self, json_var, items_schema):
        """Build constraints for array items."""
        # TODO: Implement items constraints
        return BoolVal(True)

    def build_length_constraints(
        self, json_var, min_items: Optional[int] = None, max_items: Optional[int] = None
    ):
        """Build array length constraints."""
        # TODO: Implement length constraints
        return BoolVal(True)
