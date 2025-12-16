"""Z3 JSON datatype definitions and type predicates."""

from typing import Dict, List, Set, Any, Tuple
from z3 import *


class JSONEncoder:
    """Handles Z3 JSON datatype creation and encoding."""

    def __init__(self, max_array_len: int = 50):
        self.max_array_len = max_array_len
        self._json_sort = None
        self._constructors = {}
        self._type_predicates = {}

    def create_json_datatype(self) -> DatatypeSort:
        """Create the Z3 JSON datatype following the specification.

        We'll use a simpler encoding to avoid recursive datatype complexity:
        - Arrays store element count and use indices for access
        - Objects use string keys with has/val arrays
        """
        if self._json_sort is not None:
            return self._json_sort

        # Create a simple JSON datatype without full recursive structure
        # We'll handle arrays and objects through constraints rather than nested datatypes
        JSON = Datatype("JSON")

        # Constructor for null
        JSON.declare("null")

        # Constructor for boolean: Bool(b: Bool)
        JSON.declare("bool", ("bool_val", BoolSort()))

        # Constructor for integer: Int(n: Int)
        JSON.declare("int", ("int_val", IntSort()))

        # Constructor for real: Real(r: Real)
        JSON.declare("real", ("real_val", RealSort()))

        # Constructor for string: Str(s: String)
        JSON.declare("str", ("str_val", StringSort()))

        # Constructor for array: Arr(len: Int)
        # Array elements will be handled via separate array variables
        JSON.declare("arr", ("len", IntSort()))

        # Constructor for object: Obj()
        # Object properties will be handled via separate array variables
        JSON.declare("obj")

        # Create the datatype
        self._json_sort = JSON.create()

        # Store constructors for easy access
        self._constructors = {
            "null": self._json_sort.null,
            "bool": self._json_sort.bool,
            "int": self._json_sort.int,
            "real": self._json_sort.real,
            "str": self._json_sort.str,
            "arr": self._json_sort.arr,
            "obj": self._json_sort.obj,
        }

        return self._json_sort

        # Create the JSON datatype using Z3's CreateDatatypes for recursive types
        JSON = Datatype("JSON")

        # Constructor for null
        JSON.declare("null")

        # Constructor for boolean: Bool(b: Bool)
        JSON.declare("bool", ("bool_val", BoolSort()))

        # Constructor for integer: Int(n: Int)
        JSON.declare("int", ("int_val", IntSort()))

        # Constructor for real: Real(r: Real)
        JSON.declare("real", ("real_val", RealSort()))

        # Constructor for string: Str(s: String)
        JSON.declare("str", ("str_val", StringSort()))

        # For recursive references, we create a forward declaration
        # Constructor for array: Arr(len: Int, elems: Array[Int, JSON])
        JSON.declare(
            "arr", ("len", IntSort()), ("elems", IntSort())
        )  # Simplified for now

        # Constructor for object: Obj(has: Array[String, Bool], val: Array[String, JSON])
        JSON.declare(
            "obj", ("has", ArraySort(StringSort(), BoolSort())), ("val", IntSort())
        )  # Simplified for now

        # Create the datatype
        self._json_sort = JSON.create()

        # Store constructors for easy access
        self._constructors = {
            "null": self._json_sort.null,
            "bool": self._json_sort.bool,
            "int": self._json_sort.int,
            "real": self._json_sort.real,
            "str": self._json_sort.str,
            "arr": self._json_sort.arr,
            "obj": self._json_sort.obj,
        }

        return self._json_sort

        # Create the JSON datatype
        JSON = Datatype("JSON")

        # Constructor for null
        JSON.declare("null")

        # Constructor for boolean: Bool(b: Bool)
        JSON.declare("bool", ("bool_val", BoolSort()))

        # Constructor for integer: Int(n: Int)
        JSON.declare("int", ("int_val", IntSort()))

        # Constructor for real: Real(r: Real)
        JSON.declare("real", ("real_val", RealSort()))

        # Constructor for string: Str(s: String)
        JSON.declare("str", ("str_val", StringSort()))

        # Constructor for array: Arr(len: Int, elems: Array[Int, JSON])
        # Note: We need to create the datatype first, then reference it
        JSON.declare("arr", ("len", IntSort()), ("elems", ArraySort(IntSort(), JSON)))

        # Constructor for object: Obj(has: Array[String, Bool], val: Array[String, JSON])
        JSON.declare(
            "obj",
            ("has", ArraySort(StringSort(), BoolSort())),
            ("val", ArraySort(StringSort(), JSON)),
        )

        # Create the datatype
        self._json_sort = JSON.create()

        # Store constructors for easy access
        self._constructors = {
            "null": self._json_sort.null,
            "bool": self._json_sort.bool,
            "int": self._json_sort.int,
            "real": self._json_sort.real,
            "str": self._json_sort.str,
            "arr": self._json_sort.arr,
            "obj": self._json_sort.obj,
        }

        return self._json_sort

    def create_type_predicates(self) -> Dict[str, FuncDeclRef]:
        """Create type predicate functions (is_null, is_bool, etc.)."""
        if self._json_sort is None:
            self.create_json_datatype()

        if self._type_predicates:
            return self._type_predicates

        # Create recognizer predicates for each constructor
        self._type_predicates = {
            "is_null": self._json_sort.is_null,
            "is_bool": self._json_sort.is_bool,
            "is_int": self._json_sort.is_int,
            "is_real": self._json_sort.is_real,
            "is_str": self._json_sort.is_str,
            "is_arr": self._json_sort.is_arr,
            "is_obj": self._json_sort.is_obj,
        }

        return self._type_predicates

    def get_json_sort(self) -> DatatypeSort:
        """Get the JSON datatype sort."""
        if self._json_sort is None:
            self.create_json_datatype()
        return self._json_sort

    def get_constructors(self) -> Dict[str, FuncDeclRef]:
        """Get the constructor functions."""
        if not self._constructors:
            self.create_json_datatype()
        return self._constructors

    def get_accessors(self) -> Dict[str, FuncDeclRef]:
        """Get accessor functions for constructor fields."""
        if self._json_sort is None:
            self.create_json_datatype()

        return {
            "bool_val": self._json_sort.bool_val,
            "int_val": self._json_sort.int_val,
            "real_val": self._json_sort.real_val,
            "str_val": self._json_sort.str_val,
            "len": self._json_sort.len,
            # Note: arrays and objects don't have elems/has/val in simplified encoding
        }

    def create_mutually_exclusive_constraints(self, json_var: ExprRef) -> BoolRef:
        """Create constraints ensuring exactly one type predicate holds."""
        predicates = self.create_type_predicates()

        # Exactly one type must hold
        return PbEq([(pred(json_var), 1) for pred in predicates.values()], 1)

    def encode_python_value(self, value: Any) -> ExprRef:
        """Encode a Python value as a Z3 JSON expression."""
        constructors = self.get_constructors()

        if value is None:
            return constructors["null"]()
        elif isinstance(value, bool):
            return constructors["bool"](BoolVal(value))
        elif isinstance(value, int):
            return constructors["int"](IntVal(value))
        elif isinstance(value, float):
            return constructors["real"](RealVal(value))
        elif isinstance(value, str):
            return constructors["str"](StringVal(value))
        elif isinstance(value, list):
            return self._encode_array(value)
        elif isinstance(value, dict):
            return self._encode_object(value)
        else:
            raise ValueError(f"Cannot encode value of type {type(value)}: {value}")

    def _encode_array(self, arr: List[Any]) -> ExprRef:
        """Encode a Python list as a Z3 JSON array."""
        constructors = self.get_constructors()
        json_sort = self.get_json_sort()

        # Create array with length
        length = IntVal(len(arr))

        # Create Z3 array and populate elements
        elems = Array("arr_elems", IntSort(), json_sort)
        constraints = []

        for i, item in enumerate(arr):
            encoded_item = self.encode_python_value(item)
            constraints.append(elems[IntVal(i)] == encoded_item)

        # For unused indices, we need to have some default value
        # This is handled by the array bounds in the schema compiler

        return constructors["arr"](length, elems)

    def _encode_object(self, obj: Dict[str, Any]) -> ExprRef:
        """Encode a Python dict as a Z3 JSON object."""
        constructors = self.get_constructors()
        json_sort = self.get_json_sort()

        # Create Z3 arrays for has and val
        has_array = Array("obj_has", StringSort(), BoolSort())
        val_array = Array("obj_val", StringSort(), json_sort)

        constraints = []

        # Set has[key] = true and val[key] = encoded_value for each key
        for key, value in obj.items():
            encoded_value = self.encode_python_value(value)
            constraints.append(has_array[StringVal(key)] == BoolVal(True))
            constraints.append(val_array[StringVal(key)] == encoded_value)

        return constructors["obj"](has_array, val_array)


class FiniteKeyUniverse:
    """Manages the finite set of object keys extracted from schemas."""

    def __init__(self):
        self.keys: Set[str] = set()

    def add_keys_from_schema(self, schema: dict) -> None:
        """Extract and add all property names from a schema."""
        self._extract_keys_recursive(schema, set())

    def _extract_keys_recursive(
        self, schema: Any, visited: Set[int], depth: int = 0
    ) -> None:
        """Recursively extract keys from schema."""
        if depth > 10:  # Prevent infinite recursion
            return

        if not isinstance(schema, dict):
            return

        # Avoid infinite recursion on circular references
        schema_id = id(schema)
        if schema_id in visited:
            return
        visited.add(schema_id)

        # Extract from properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            self.keys.update(schema["properties"].keys())

            # Recursively process property schemas
            for prop_schema in schema["properties"].values():
                self._extract_keys_recursive(prop_schema, visited, depth + 1)

        # Extract from patternProperties
        if "patternProperties" in schema and isinstance(
            schema["patternProperties"], dict
        ):
            self.keys.update(schema["patternProperties"].keys())

            # Recursively process pattern schemas
            for pattern_schema in schema["patternProperties"].values():
                self._extract_keys_recursive(pattern_schema, visited, depth + 1)

        # Recursively process nested schemas
        for key, value in schema.items():
            if key in ["allOf", "anyOf", "oneOf"]:
                if isinstance(value, list):
                    for subschema in value:
                        self._extract_keys_recursive(subschema, visited, depth + 1)
            elif key in ["not", "items", "additionalProperties"]:
                self._extract_keys_recursive(value, visited, depth + 1)
            elif key in ["then", "else"]:
                self._extract_keys_recursive(value, visited, depth + 1)
            elif key == "if":
                self._extract_keys_recursive(value, visited, depth + 1)

    def get_key_list(self) -> List[str]:
        """Get ordered list of all keys."""
        return sorted(self.keys)
