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
            if any(k in schema for k in ["minLength", "maxLength", "pattern"]):
                constraints.append(self.compile_string_constraints(json_var, schema))

            # Handle object constraints
            if any(
                k in schema for k in ["properties", "required", "additionalProperties"]
            ):
                constraints.append(self.compile_object_constraints(json_var, schema))

            # Handle array constraints
            if any(k in schema for k in ["items", "minItems", "maxItems"]):
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
            int_constraints.append(int_val(json_var) >= IntVal(minimum))
        if maximum is not None:
            int_constraints.append(int_val(json_var) <= IntVal(maximum))
        if exclusive_minimum is not None:
            int_constraints.append(int_val(json_var) > IntVal(exclusive_minimum))
        if exclusive_maximum is not None:
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
            real_constraints.append(real_val(json_var) >= RealVal(minimum))
        if maximum is not None:
            real_constraints.append(real_val(json_var) <= RealVal(maximum))
        if exclusive_minimum is not None:
            real_constraints.append(real_val(json_var) > RealVal(exclusive_minimum))
        if exclusive_maximum is not None:
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
