"""Custom exceptions for jsound."""


class JSoundError(Exception):
    """Base exception for jsound."""

    pass


class UnsupportedFeatureError(JSoundError):
    """Raised when encountering unsupported JSON Schema features."""

    pass


class SchemaValidationError(JSoundError):
    """Raised when schema validation fails."""

    pass


class SolverTimeoutError(JSoundError):
    """Raised when Z3 solver times out."""

    pass


class CounterexampleExtractionError(JSoundError):
    """Raised when counterexample extraction fails."""

    pass


class CyclicSchemaError(JSoundError):
    """Raised when cyclic references are detected in unfolding-only mode."""

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
