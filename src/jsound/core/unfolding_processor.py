"""Unfolding processor for complete expansion of acyclic JSON schemas."""

from typing import Any, Dict, List, Union
# Import will be fixed later when dependencies are resolved
# from .schema_registry import SchemaRegistry


# Temporary workaround for import issues
class CyclicSchemaError(Exception):
    def __init__(self, message: str, cycles=None):
        super().__init__(message)
        self.cycles = cycles or {}

    def __str__(self):
        if not self.cycles:
            return super().__str__()

        cycle_descriptions = []
        for cycle_id, cycle_refs in self.cycles.items():
            cycle_descriptions.append(f"  {cycle_id}: {' -> '.join(cycle_refs)}")

        return (
            f"{super().__str__()}\n\nDetected cycles:\n"
            + "\n".join(cycle_descriptions)
            + f"\n\nSuggestion: Use --ref-resolution-strategy=simulation for recursive schemas."
        )


class UnfoldingProcessor:
    """Handles complete unfolding of acyclic JSON schemas with $ref resolution."""

    def __init__(self, registry):
        """Initialize processor with schema registry."""
        self.registry = registry
        self.unfolding_cache = {}  # Cache for resolved references

    def unfold_schema(self, schema: dict) -> dict:
        """
        Main entry point: unfold schema or fail if cycles detected.

        Args:
            schema: Root schema to unfold

        Returns:
            Completely unfolded schema with no $ref remaining

        Raises:
            CyclicSchemaError: If cycles are detected in the reference graph
        """
        if self.registry.has_cycles():
            cycle_info = self.registry.get_cycle_info()
            raise CyclicSchemaError(
                "Cyclic references detected. Use simulation-based resolution instead.",
                cycles=cycle_info,
            )

        return self._complete_unfold(schema)

    def _complete_unfold(self, schema: Any) -> Any:
        """
        Completely expand all references (acyclic case only).

        Strategy: Recursive substitution with caching
        1. If schema contains $ref, resolve and recursively unfold
        2. Cache resolved references to avoid recomputation
        3. Recursively process nested schemas
        4. Result: Schema with zero $ref remaining

        Precondition: No cycles in reference graph
        Postcondition: Returned schema contains no $ref
        """
        if isinstance(schema, dict) and "$ref" in schema:
            ref_uri = schema["$ref"]

            # Check cache first
            if ref_uri in self.unfolding_cache:
                return self.unfolding_cache[ref_uri]

            # Resolve and recursively unfold
            try:
                resolved = self.registry.resolve_ref(ref_uri)
                unfolded = self._complete_unfold(resolved)

                # Cache result
                self.unfolding_cache[ref_uri] = unfolded
                return unfolded
            except Exception as e:
                # Re-raise with more context
                raise Exception(f"Failed to resolve reference {ref_uri}: {e}")

        # Recursively process nested schemas
        return self._recursive_unfold_complete(schema)

    def _recursive_unfold_complete(self, schema: Any) -> Any:
        """Recursively unfold all nested schema structures."""
        if isinstance(schema, dict):
            unfolded = {}
            for key, value in schema.items():
                if key == "$ref":
                    # Should not reach here if cycle detection worked
                    continue
                else:
                    unfolded[key] = self._complete_unfold(value)
            return unfolded

        elif isinstance(schema, list):
            return [self._complete_unfold(item) for item in schema]

        else:
            # Primitive values (string, int, bool, null) pass through unchanged
            return schema

    def clear_cache(self):
        """Clear the unfolding cache (useful between schema comparisons)."""
        self.unfolding_cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for debugging/optimization."""
        return {
            "cache_size": len(self.unfolding_cache),
            "cached_refs": list(self.unfolding_cache.keys()),
        }
