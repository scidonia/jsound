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
