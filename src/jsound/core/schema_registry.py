"""Schema registry for managing JSON Schema definitions and reference resolution."""

from typing import Dict, Set, List, Optional, Any


# Temporary workaround for import issues
class SchemaValidationError(Exception):
    pass


class SchemaRegistry:
    """Manages schema definitions and resolves $ref URIs with cycle detection."""

    def __init__(self, root_schema: dict):
        """Initialize registry with root schema and detect cycles."""
        self.root_schema = root_schema
        self.definitions = self._extract_definitions(root_schema)
        self.ref_graph = self._build_reference_graph()
        self.cycles = self._detect_cycles()

    def resolve_ref(self, ref_uri: str) -> dict:
        """Resolve a $ref URI to its schema definition."""
        # Handle JSON Pointer references
        if ref_uri.startswith("#/"):
            return self._resolve_json_pointer(ref_uri)
        else:
            raise SchemaValidationError(f"Unsupported reference format: {ref_uri}")

    def has_cycles(self) -> bool:
        """Check if the schema has any reference cycles."""
        return len(self.cycles) > 0

    def get_cycle_info(self) -> Dict[str, List[str]]:
        """Return detailed cycle information for debugging."""
        return self.cycles.copy()

    def _extract_definitions(self, schema: dict) -> Dict[str, dict]:
        """Extract all $defs and definitions from schema."""
        definitions = {}

        # Extract from $defs (JSON Schema Draft 2019-09+)
        if "$defs" in schema:
            for name, defn in schema["$defs"].items():
                definitions[f"#/$defs/{name}"] = defn

        # Extract from definitions (older drafts)
        if "definitions" in schema:
            for name, defn in schema["definitions"].items():
                definitions[f"#/definitions/{name}"] = defn

        return definitions

    def _resolve_json_pointer(self, ref_uri: str) -> dict:
        """Resolve JSON Pointer reference."""
        # Handle #/$defs/Name format
        if ref_uri.startswith("#/$defs/"):
            def_name = ref_uri[8:]  # Remove "#/$defs/"
            if ref_uri in self.definitions:
                return self.definitions[ref_uri]
            else:
                raise SchemaValidationError(f"Definition not found: {def_name}")

        # Handle #/definitions/Name format
        elif ref_uri.startswith("#/definitions/"):
            def_name = ref_uri[14:]  # Remove "#/definitions/"
            if ref_uri in self.definitions:
                return self.definitions[ref_uri]
            else:
                raise SchemaValidationError(f"Definition not found: {def_name}")

        else:
            raise SchemaValidationError(f"Unsupported JSON Pointer: {ref_uri}")

    def _build_reference_graph(self) -> Dict[str, Set[str]]:
        """Build directed graph of $ref dependencies."""
        graph = {}

        # Add all definitions as nodes
        for def_uri in self.definitions:
            graph[def_uri] = set()

        # Find references in each definition
        for def_uri, definition in self.definitions.items():
            refs = self._find_refs_in_schema(definition)
            graph[def_uri] = refs

        # Also check root schema for references
        root_refs = self._find_refs_in_schema(self.root_schema)
        if root_refs:
            graph["#"] = root_refs

        return graph

    def _find_refs_in_schema(self, schema: Any) -> Set[str]:
        """Recursively find all $ref URIs in a schema."""
        refs = set()

        if isinstance(schema, dict):
            if "$ref" in schema:
                refs.add(schema["$ref"])

            # Recursively search in all values
            for value in schema.values():
                refs.update(self._find_refs_in_schema(value))

        elif isinstance(schema, list):
            # Recursively search in all list items
            for item in schema:
                refs.update(self._find_refs_in_schema(item))

        return refs

    def _detect_cycles(self) -> Dict[str, List[str]]:
        """Detect all cycles using Tarjan's strongly connected components algorithm."""
        # Tarjan's algorithm state
        index_counter = [0]  # Use list to allow modification in nested function
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        cycles = {}

        def strongconnect(node):
            """Tarjan's strongconnect subroutine."""
            # Set the depth index for this node
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            # Consider successors
            if node in self.ref_graph:
                for successor in self.ref_graph[node]:
                    if successor not in self.definitions and successor != "#":
                        # Skip external or invalid references
                        continue

                    if successor not in index:
                        # Successor has not yet been visited; recurse on it
                        strongconnect(successor)
                        lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                    elif on_stack.get(successor, False):
                        # Successor is in stack and hence in current SCC
                        lowlinks[node] = min(lowlinks[node], index[successor])

            # If node is a root node, pop the stack and generate an SCC
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break

                # If component has more than one node or self-loop, it's a cycle
                if len(component) > 1 or (
                    len(component) == 1 and node in self.ref_graph.get(node, set())
                ):
                    cycle_id = f"cycle_{len(cycles) + 1}"
                    cycles[cycle_id] = component

        # Run Tarjan's algorithm
        for node in self.ref_graph:
            if node not in index:
                strongconnect(node)

        return cycles
