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
            # Check for unresolved $ref (should be resolved by unfolding processor first)
            if isinstance(schema, dict) and "$ref" in schema:
                raise UnsupportedFeatureError(
                    f"Unresolved $ref found: {schema['$ref']}. Schema should be unfolded before compilation."
                )

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
            if any(
                k in schema for k in ["minLength", "maxLength", "pattern", "format"]
            ):
                constraints.append(self.compile_string_constraints(json_var, schema))

            # Handle object constraints
            if any(
                k in schema for k in ["properties", "required", "additionalProperties"]
            ):
                constraints.append(self.compile_object_constraints(json_var, schema))

            # Handle array constraints
            if any(k in schema for k in ["items", "minItems", "maxItems", "contains"]):
                constraints.append(self.compile_array_constraints(json_var, schema))

            # Handle number constraints
            if any(
                k in schema
                for k in [
                    "minimum",
                    "maximum",
                    "exclusiveMinimum",
                    "exclusiveMaximum",
                    "multipleOf",
                ]
            ):
                constraints.append(self.compile_number_constraints(json_var, schema))

            # Handle if/then/else conditionals
            if any(k in schema for k in ["if", "then", "else"]):
                constraints.append(
                    self.compile_conditional_constraints(json_var, schema)
                )

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

        # Handle format constraint
        if "format" in schema:
            format_name = schema["format"]
            try:
                format_constraint = self._compile_format_constraint(
                    str_val, format_name
                )
                constraints.append(format_constraint)
            except Exception as e:
                raise UnsupportedFeatureError(
                    f"Format '{format_name}' not supported: {e}"
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

    def _compile_format_constraint(self, str_val, format_name):
        """Compile format constraints using regex patterns or domain-specific logic.

        For schema subsumption, format constraints are important because:
        - Same format ⊆ same format (always true)
        - Specific format ⊆ no format (more restrictive ⊆ less restrictive)
        - Different formats usually incompatible
        """

        # Define regex patterns for common formats
        format_patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "uri": r"^https?://[^\s/$.?#].[^\s]*$",
            "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            "date": r"^\d{4}-\d{2}-\d{2}$",
            "date-time": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})$",
            "time": r"^\d{2}:\d{2}:\d{2}(?:\.\d{3})?$",
            "ipv4": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
            "ipv6": r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$",
        }

        if format_name in format_patterns:
            pattern = format_patterns[format_name]
            # For Z3, we'll use a simplified version that captures the essence
            # Full regex matching in Z3 is complex, so we use approximations

            if format_name == "email":
                # Simplified: contains @ and has chars before and after
                # Build pattern: .+@.+
                any_char = Union(
                    Range("a", "z"),
                    Range("A", "Z"),
                    Range("0", "9"),
                    Re("."),
                    Re("_"),
                    Re("-"),
                )
                at_sign = Re("@")
                email_pattern = Concat(Plus(any_char), at_sign, Plus(any_char))
                return And(
                    InRe(str_val, email_pattern),
                    Length(str_val) >= IntVal(5),  # minimum reasonable email length
                )
            elif format_name == "uri":
                # Simplified: starts with http:// or https://
                # Build pattern: http(s)?://.*
                any_char = Union(
                    Range("a", "z"),
                    Range("A", "Z"),
                    Range("0", "9"),
                    Re("."),
                    Re("/"),
                    Re("-"),
                    Re("_"),
                )
                http_pattern = Concat(
                    Re("http"), Option(Re("s")), Re("://"), Star(any_char)
                )
                ftp_pattern = Concat(Re("ftp://"), Star(any_char))
                return Or(InRe(str_val, http_pattern), InRe(str_val, ftp_pattern))
                ftp_pattern = Concat(Re("ftp://"), Star(any_char))
                return Or(InRe(str_val, http_pattern), InRe(str_val, ftp_pattern))
            elif format_name == "uuid":
                # Simplified: correct length and contains hyphens at right positions
                hex_char = Union(Range("0", "9"), Range("a", "f"), Range("A", "F"))
                dash = Re("-")
                uuid_pattern = Concat(
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    dash,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    dash,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    dash,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    dash,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                    hex_char,
                )
                return And(Length(str_val) == IntVal(36), InRe(str_val, uuid_pattern))
            elif format_name == "date":
                # Construct proper Z3 regex for YYYY-MM-DD format
                # [0-9]{4} for year
                digit = Range("0", "9")
                year_part = Concat(digit, digit, digit, digit)
                # Dash
                dash = Re("-")
                # [0-9]{2} for month
                month_part = Concat(digit, digit)
                # [0-9]{2} for day
                day_part = Concat(digit, digit)
                # Complete pattern: YYYY-MM-DD
                date_pattern = Concat(year_part, dash, month_part, dash, day_part)

                return And(
                    Length(str_val) == IntVal(10),
                    InRe(str_val, date_pattern),
                )
            elif format_name == "date-time":
                # Simplified: YYYY-MM-DDTHH:MM:SS format
                digit = Range("0", "9")
                dash = Re("-")
                colon = Re(":")
                t_char = Re("T")
                # Date part: YYYY-MM-DD
                date_part = Concat(
                    digit, digit, digit, digit, dash, digit, digit, dash, digit, digit
                )
                # Time part: HH:MM:SS
                time_part = Concat(
                    digit, digit, colon, digit, digit, colon, digit, digit
                )
                datetime_pattern = Concat(date_part, t_char, time_part)
                return And(
                    Length(str_val) >= IntVal(19),  # minimum for YYYY-MM-DDTHH:MM:SS
                    InRe(str_val, datetime_pattern),
                )
            elif format_name == "time":
                # Simplified: HH:MM:SS format
                digit = Range("0", "9")
                colon = Re(":")
                time_pattern = Concat(
                    digit, digit, colon, digit, digit, colon, digit, digit
                )
                return And(
                    Length(str_val) >= IntVal(8),
                    InRe(str_val, time_pattern),
                )
            elif format_name in ["ipv4", "ipv6"]:
                if format_name == "ipv4":
                    # Simplified: digits and dots
                    digit = Range("0", "9")
                    dot = Re(".")
                    ipv4_pattern = Concat(
                        Plus(digit),
                        dot,
                        Plus(digit),
                        dot,
                        Plus(digit),
                        dot,
                        Plus(digit),
                    )
                    return And(
                        InRe(str_val, ipv4_pattern),
                        Length(str_val) >= IntVal(7),  # minimum 0.0.0.0
                    )
                else:  # ipv6
                    # Simplified: hex chars and colons
                    hex_char = Union(Range("0", "9"), Range("a", "f"), Range("A", "F"))
                    colon = Re(":")
                    ipv6_pattern = Concat(
                        Plus(hex_char), Star(Concat(colon, Plus(hex_char)))
                    )
                    return And(
                        InRe(str_val, ipv6_pattern),
                        Length(str_val) >= IntVal(2),
                    )

        # For unknown formats, create a symbolic constraint
        # This allows format checking in subsumption without full validation
        else:
            # Create a predicate symbol for this specific format
            format_pred = Bool(f"format_{format_name}")
            # For subsumption checking, we assume the format constraint exists
            # but don't validate its actual content
            return format_pred

    def compile_object_constraints(self, json_var, schema):
        """Compile object-specific constraints (properties, required, additionalProperties)."""
        constraints = []

        # First ensure it's an object type
        predicates = self.json_encoder.create_type_predicates()
        is_obj = predicates["is_obj"]
        constraints.append(is_obj(json_var))

        # Create object constraint builder
        obj_builder = ObjectConstraintBuilder(self.json_encoder, self.key_universe)

        # Handle properties
        if "properties" in schema:
            property_constraint = obj_builder.build_property_constraints(
                json_var, schema["properties"], self.compile_schema
            )
            constraints.append(property_constraint)

        # Handle required properties
        if "required" in schema:
            required_constraint = obj_builder.build_required_constraints(
                json_var, schema["required"]
            )
            constraints.append(required_constraint)

        # Handle patternProperties
        if "patternProperties" in schema:
            pattern_constraint = obj_builder.build_pattern_properties_constraints(
                json_var, schema["patternProperties"], self.compile_schema
            )
            constraints.append(pattern_constraint)

        # Handle additionalProperties
        if "additionalProperties" in schema:
            additional_constraint = obj_builder.build_additional_properties_constraints(
                json_var,
                schema["additionalProperties"],
                schema.get("properties", {}),
                self.compile_schema,
            )
            constraints.append(additional_constraint)

        # Combine all constraints
        if len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)

    def compile_array_constraints(self, json_var, schema):
        """Compile array-specific constraints per JSON Schema spec section 8."""
        builder = ArrayConstraintBuilder()

        constraints = []

        # Handle items constraints
        if "items" in schema:
            items_constraint = builder.build_items_constraints(
                json_var, schema["items"], self
            )
            constraints.append(items_constraint)

        # Handle length constraints
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None or max_items is not None:
            length_constraint = builder.build_length_constraints(
                json_var, min_items, max_items, json_encoder=self.json_encoder
            )
            constraints.append(length_constraint)

        # Handle contains constraints
        if "contains" in schema:
            contains_constraint = builder.build_contains_constraints(
                json_var, schema["contains"], self
            )
            constraints.append(contains_constraint)

        # Handle uniqueItems constraints
        if schema.get("uniqueItems") is True:
            unique_constraint = builder.build_unique_items_constraints(
                json_var, self.json_encoder
            )
            constraints.append(unique_constraint)

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)

    def compile_number_constraints(self, json_var, schema):
        """Compile number-specific constraints per JSON Schema spec section 10."""
        # Get type predicates and accessors
        type_predicates = self.json_encoder.create_type_predicates()
        accessors = self.json_encoder.get_accessors()
        is_int = type_predicates["is_int"]
        is_real = type_predicates["is_real"]
        int_val = accessors["int_val"]
        real_val = accessors["real_val"]

        constraints = []

        # Extract number constraint parameters
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        exclusive_minimum = schema.get("exclusiveMinimum")
        exclusive_maximum = schema.get("exclusiveMaximum")
        multiple_of = schema.get("multipleOf")

        # Build bounds constraints for integers
        int_constraints = []
        if minimum is not None:
            if exclusive_minimum is True:
                # JSON Schema Draft 7: exclusiveMinimum: true means minimum is exclusive
                int_constraints.append(int_val(json_var) > IntVal(minimum))
            else:
                int_constraints.append(int_val(json_var) >= IntVal(minimum))
        if maximum is not None:
            if exclusive_maximum is True:
                # JSON Schema Draft 7: exclusiveMaximum: true means maximum is exclusive
                int_constraints.append(int_val(json_var) < IntVal(maximum))
            else:
                int_constraints.append(int_val(json_var) <= IntVal(maximum))
        # Handle numeric exclusiveMinimum/exclusiveMaximum (JSON Schema Draft 6 style)
        if exclusive_minimum is not None and not isinstance(exclusive_minimum, bool):
            int_constraints.append(int_val(json_var) > IntVal(exclusive_minimum))
        if exclusive_maximum is not None and not isinstance(exclusive_maximum, bool):
            int_constraints.append(int_val(json_var) < IntVal(exclusive_maximum))

        if int_constraints:
            int_constraint = (
                And(*int_constraints)
                if len(int_constraints) > 1
                else int_constraints[0]
            )
            constraints.append(Implies(is_int(json_var), int_constraint))

        # Build bounds constraints for reals
        real_constraints = []
        if minimum is not None:
            if exclusive_minimum is True:
                # JSON Schema Draft 7: exclusiveMinimum: true means minimum is exclusive
                real_constraints.append(real_val(json_var) > RealVal(minimum))
            else:
                real_constraints.append(real_val(json_var) >= RealVal(minimum))
        if maximum is not None:
            if exclusive_maximum is True:
                # JSON Schema Draft 7: exclusiveMaximum: true means maximum is exclusive
                real_constraints.append(real_val(json_var) < RealVal(maximum))
            else:
                real_constraints.append(real_val(json_var) <= RealVal(maximum))
        # Handle numeric exclusiveMinimum/exclusiveMaximum (JSON Schema Draft 6 style)
        if exclusive_minimum is not None and not isinstance(exclusive_minimum, bool):
            real_constraints.append(real_val(json_var) > RealVal(exclusive_minimum))
        if exclusive_maximum is not None and not isinstance(exclusive_maximum, bool):
            real_constraints.append(real_val(json_var) < RealVal(exclusive_maximum))

        if real_constraints:
            real_constraint = (
                And(*real_constraints)
                if len(real_constraints) > 1
                else real_constraints[0]
            )
            constraints.append(Implies(is_real(json_var), real_constraint))

        # Build multipleOf constraint (only for integers)
        if multiple_of is not None:
            multiple_constraint = (int_val(json_var) % IntVal(multiple_of)) == IntVal(0)
            constraints.append(Implies(is_int(json_var), multiple_constraint))

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)

    def compile_conditional_constraints(self, json_var, schema):
        """Compile if/then/else conditional constraints per JSON Schema Draft 7.

        The logic is:
        - if condition AND then_schema: (condition → then_constraint)
        - if condition AND else_schema: (¬condition → else_constraint)
        - Both can be present simultaneously
        """
        if_schema = schema.get("if")
        then_schema = schema.get("then")
        else_schema = schema.get("else")

        constraints = []

        if if_schema:
            if_constraint = self.compile_schema(if_schema, json_var)

            # If-then: when condition holds, then_schema must be satisfied
            if then_schema:
                then_constraint = self.compile_schema(then_schema, json_var)
                constraints.append(Implies(if_constraint, then_constraint))

            # If-else: when condition doesn't hold, else_schema must be satisfied
            if else_schema:
                else_constraint = self.compile_schema(else_schema, json_var)
                constraints.append(Implies(Not(if_constraint), else_constraint))

        # Handle edge cases: then/else without if (uncommon but valid)
        elif then_schema and not if_schema:
            # then without if means always apply then_schema
            then_constraint = self.compile_schema(then_schema, json_var)
            constraints.append(then_constraint)

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)


class ObjectConstraintBuilder:
    """Handles object-specific constraint building per specification section 7."""

    def __init__(self, json_encoder, key_universe):
        self.json_encoder = json_encoder
        self.key_universe = key_universe

    def build_property_constraints(self, json_var, properties, compile_func):
        """Build constraints for object properties.

        Per spec section 7.2: For each property `k` with schema `Sk`:
        has(j,k) → ⟦Sk⟧(val(j,k))
        """
        if not properties:
            return BoolVal(True)

        # Get object access functions
        obj_functions = self.json_encoder.get_object_functions()
        has_func = obj_functions["has"]
        val_func = obj_functions["val"]

        constraints = []
        for property_name, property_schema in properties.items():
            # Create string literal for property name
            key_literal = StringVal(property_name)

            # has(j, k) → ⟦Sk⟧(val(j, k))
            # If the object has this property, then the value must satisfy the schema
            has_property = has_func(json_var, key_literal)
            property_value = val_func(json_var, key_literal)

            # Compile the property schema constraint using passed function
            property_constraint = compile_func(property_schema, property_value)

            # Add implication: has(j, k) → constraint
            constraints.append(Implies(has_property, property_constraint))

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)

    def build_required_constraints(self, json_var, required):
        """Build constraints for required properties.

        Per spec section 7.1: For each `k ∈ required`:
        is_obj(j) → has(j,k)
        """
        if not required:
            return BoolVal(True)

        # Get type predicates and object functions
        type_predicates = self.json_encoder.create_type_predicates()
        obj_functions = self.json_encoder.get_object_functions()
        is_obj = type_predicates["is_obj"]
        has_func = obj_functions["has"]

        constraints = []
        for property_name in required:
            # Create string literal for property name
            key_literal = StringVal(property_name)

            # is_obj(j) → has(j,k)
            # If it's an object, it must have this required property
            is_object = is_obj(json_var)
            has_property = has_func(json_var, key_literal)

            constraints.append(Implies(is_object, has_property))

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)

    def build_additional_properties_constraints(
        self, json_var, additional_properties, declared_properties, compile_func
    ):
        """Build constraints for additionalProperties.

        Per spec section 7.3:
        - If false: ∀ k ∈ Keys \ declared: has(j,k) == false
        - If schema S: has(j,k) ∧ k not declared → ⟦S⟧(val(j,k))
        """
        if additional_properties is None:
            # Default behavior - allow any additional properties
            return BoolVal(True)

        # Get the finite key universe and object functions
        obj_functions = self.json_encoder.get_object_functions()
        has_func = obj_functions["has"]
        val_func = obj_functions["val"]

        # Get all keys that are not explicitly declared
        declared_keys = (
            set(declared_properties.keys()) if declared_properties else set()
        )
        undeclared_keys = self.key_universe.keys - declared_keys

        constraints = []

        if additional_properties is False:
            # additionalProperties: false - no undeclared properties allowed
            for key in undeclared_keys:
                key_literal = StringVal(key)
                has_undeclared = has_func(json_var, key_literal)
                constraints.append(Not(has_undeclared))

        elif isinstance(additional_properties, dict):
            # additionalProperties: schema - undeclared properties must satisfy schema
            for key in undeclared_keys:
                key_literal = StringVal(key)
                has_undeclared = has_func(json_var, key_literal)
                property_value = val_func(json_var, key_literal)

                # Compile the additional property schema using passed function
                additional_constraint = compile_func(
                    additional_properties, property_value
                )

                # has(j,k) → constraint (only for undeclared keys)
                constraints.append(Implies(has_undeclared, additional_constraint))

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)

    def build_pattern_properties_constraints(
        self, json_var, pattern_properties, compile_func
    ):
        """Build constraints for patternProperties.

        Per JSON Schema spec: For each pattern P with schema SP:
        ∀ k ∈ Keys: matches(k, P) ∧ has(j,k) → ⟦SP⟧(val(j,k))
        """
        import re

        if not pattern_properties:
            return BoolVal(True)

        # Get object access functions
        obj_functions = self.json_encoder.get_object_functions()
        has_func = obj_functions["has"]
        val_func = obj_functions["val"]

        constraints = []

        # For each pattern and its schema
        for pattern, pattern_schema in pattern_properties.items():
            # For each key in the key universe, check if it matches the pattern
            for key in self.key_universe.keys:
                try:
                    if re.match(pattern, key):
                        # This key matches the pattern
                        key_literal = StringVal(key)
                        has_property = has_func(json_var, key_literal)
                        property_value = val_func(json_var, key_literal)

                        # Compile the pattern schema constraint
                        pattern_constraint = compile_func(
                            pattern_schema, property_value
                        )

                        # has(j, k) → pattern_constraint (for matching keys)
                        constraints.append(Implies(has_property, pattern_constraint))

                except re.error:
                    # Invalid regex pattern - skip silently
                    pass

        if not constraints:
            return BoolVal(True)
        elif len(constraints) == 1:
            return constraints[0]
        else:
            return And(*constraints)


class ArrayConstraintBuilder:
    """Handles array-specific constraint building."""

    def build_items_constraints(self, json_var, items_schema, compiler):
        """Build constraints for array items per z3-jsonschema-arrays-guidance.md.

        Uses the recommended bounded quantifier-free approach:
        - Choose MAX_ARRAY_LEN and unroll constraints for each index
        - For each i, add: Implies(i < len, Sat(items_schema, elems[i]))
        """
        MAX_ARRAY_LEN = 8  # As recommended by guidance

        # Get array type predicate and accessors
        type_predicates = compiler.json_encoder.create_type_predicates()
        accessors = compiler.json_encoder.get_accessors()
        is_arr = type_predicates["is_arr"]
        arr_len = accessors["len"]  # This gives us len field from array

        # Create external array elements function as recommended by guidance
        # arr_elems: JSON -> Array[Int, JSON]
        json_sort = compiler.json_encoder.get_json_sort()
        arr_elems = Function("arr_elems", json_sort, ArraySort(IntSort(), json_sort))

        # Build constraints for each possible index (bounded approach)
        i_constraints = []
        for i in range(MAX_ARRAY_LEN):
            # For index i: if array is valid and i < length, then element i satisfies item schema
            element_at_i = Select(arr_elems(json_var), IntVal(i))
            item_constraint = compiler.compile_schema(items_schema, element_at_i)

            i_constraints.append(
                Implies(
                    And(is_arr(json_var), IntVal(i) < arr_len(json_var)),
                    item_constraint,
                )
            )

        # Add bounds constraint: 0 ≤ len ≤ MAX_ARRAY_LEN
        bounds = Implies(
            is_arr(json_var),
            And(arr_len(json_var) >= 0, arr_len(json_var) <= MAX_ARRAY_LEN),
        )

        # Combine all constraints
        return And(bounds, *i_constraints)

    def build_length_constraints(
        self,
        json_var,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        json_encoder=None,
    ):
        """Build array length constraints."""
        if min_items is None and max_items is None:
            return BoolVal(True)

        if json_encoder is None:
            raise ValueError("json_encoder is required for length constraints")

        # Get array type predicate and length accessor
        type_predicates = json_encoder.create_type_predicates()
        accessors = json_encoder.get_accessors()
        is_arr = type_predicates["is_arr"]
        len_func = accessors["len"]

        # Get the array length
        array_len = len_func(json_var)

        constraints = []

        # Add minimum length constraint
        if min_items is not None:
            constraints.append(array_len >= IntVal(min_items))

        # Add maximum length constraint
        if max_items is not None:
            constraints.append(array_len <= IntVal(max_items))

        if not constraints:
            return BoolVal(True)

        # Apply constraints only to arrays
        if len(constraints) == 1:
            constraint = constraints[0]
        else:
            constraint = And(*constraints)

        return Implies(is_arr(json_var), constraint)

    def build_contains_constraints(self, json_var, contains_schema, compiler):
        """Build contains constraints for arrays.

        The 'contains' keyword validates that at least one element in the array
        satisfies the given schema. This is implemented using existential
        quantification: ∃i ∈ [0, len-1] such that element[i] satisfies contains_schema.

        Uses bounded approach similar to items constraints.
        """
        MAX_ARRAY_LEN = 8  # Same as items constraints

        # Get array type predicate and accessors
        type_predicates = compiler.json_encoder.create_type_predicates()
        accessors = compiler.json_encoder.get_accessors()
        is_arr = type_predicates["is_arr"]
        arr_len = accessors["len"]

        # Create external array elements function
        json_sort = compiler.json_encoder.get_json_sort()
        arr_elems = Function("arr_elems", json_sort, ArraySort(IntSort(), json_sort))

        # Build existential constraint: there exists at least one valid element
        # OR over all possible indices i where i < len and element[i] satisfies schema
        exists_constraints = []
        for i in range(MAX_ARRAY_LEN):
            element_at_i = Select(arr_elems(json_var), IntVal(i))
            element_satisfies_schema = compiler.compile_schema(
                contains_schema, element_at_i
            )

            # This element exists (i < len) AND satisfies the contains schema
            element_valid = And(IntVal(i) < arr_len(json_var), element_satisfies_schema)
            exists_constraints.append(element_valid)

        # At least one element must satisfy the constraint
        contains_constraint = Or(*exists_constraints)

        # Only apply to non-empty arrays (contains has no effect on empty arrays)
        # Per JSON Schema spec: "contains" succeeds on empty arrays
        return Implies(
            And(is_arr(json_var), arr_len(json_var) > 0), contains_constraint
        )

    def build_unique_items_constraints(self, json_var, json_encoder):
        """Build uniqueItems constraints for arrays.

        The 'uniqueItems' keyword validates that all elements in the array are unique.
        This is implemented using pairwise inequality constraints:
        ∀i,j ∈ [0, len-1]: i ≠ j → element[i] ≠ element[j]

        Uses bounded approach with MAX_ARRAY_LEN limit.
        """
        MAX_ARRAY_LEN = 8  # Same as other array constraints

        # Get array type predicate and accessors
        type_predicates = json_encoder.create_type_predicates()
        accessors = json_encoder.get_accessors()
        is_arr = type_predicates["is_arr"]
        arr_len = accessors["len"]

        # Create external array elements function
        json_sort = json_encoder.get_json_sort()
        arr_elems = Function("arr_elems", json_sort, ArraySort(IntSort(), json_sort))

        # Build pairwise inequality constraints
        # For each pair of distinct indices i,j: if both are valid, then elements must be different
        unique_constraints = []
        for i in range(MAX_ARRAY_LEN):
            for j in range(
                i + 1, MAX_ARRAY_LEN
            ):  # j > i to avoid redundant comparisons
                element_i = Select(arr_elems(json_var), IntVal(i))
                element_j = Select(arr_elems(json_var), IntVal(j))

                # Both indices are within bounds
                both_valid = And(
                    IntVal(i) < arr_len(json_var), IntVal(j) < arr_len(json_var)
                )

                # Elements at these positions must be different
                elements_different = element_i != element_j

                unique_constraints.append(Implies(both_valid, elements_different))

        # Apply uniqueness constraint only to arrays
        if not unique_constraints:
            return BoolVal(True)
        elif len(unique_constraints) == 1:
            constraint = unique_constraints[0]
        else:
            constraint = And(*unique_constraints)

        return Implies(is_arr(json_var), constraint)
