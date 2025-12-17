"""
JSO's clean library interface for subsumption testing.

This module provides a simple, clean API for testing schema subsumption
without depending on CLI or complex configuration.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import the real Z3-based implementations
from .core.subsumption import SubsumptionChecker, SolverConfig
from .exceptions import JSoundError, UnsupportedFeatureError


@dataclass
class SubsumptionResult:
    """Result of a subsumption check."""

    is_compatible: bool
    counterexample: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    solver_time: Optional[float] = None
    requires_simulation: bool = False


class JSoundAPI:
    """
    Simple API for JSON Schema subsumption checking.

    Usage:
        api = JSoundAPI()
        result = api.check_subsumption(producer_schema, consumer_schema)

        if result.is_compatible:
            print("Producer ⊆ Consumer")
        else:
            print(f"Incompatible: {result.counterexample}")
    """

    def __init__(
        self,
        timeout: int = 30,
        max_array_length: int = 50,
        ref_resolution_strategy: str = "unfold",
    ):
        """
        Initialize the JSO API.

        Args:
            timeout: Z3 solver timeout in seconds
            max_array_length: Maximum array length for bounds
            ref_resolution_strategy: 'unfold' (acyclic only) or 'simulation' (future)
        """
        self.config = SolverConfig(
            timeout=timeout,
            max_array_len=max_array_length,
            ref_resolution_strategy=ref_resolution_strategy,
        )

    def check_subsumption(
        self, producer_schema: Dict[str, Any], consumer_schema: Dict[str, Any]
    ) -> SubsumptionResult:
        """
        Check if producer schema is subsumed by consumer schema.

        Args:
            producer_schema: The producer JSON schema (more specific)
            consumer_schema: The consumer JSON schema (more general)

        Returns:
            SubsumptionResult with compatibility status and details

        Note:
            Returns True if producer ⊆ consumer, meaning every value
            that satisfies the producer schema also satisfies the consumer schema.
        """
        try:
            # Use the real Z3-based subsumption checker
            checker = SubsumptionChecker(self.config)
            result = checker.check_subsumption(producer_schema, consumer_schema)

            # Convert from CheckResult to SubsumptionResult
            return SubsumptionResult(
                is_compatible=result.is_compatible,
                counterexample=result.counterexample,
                solver_time=result.solver_time,
                error_message=result.error_message,
            )

        except UnsupportedFeatureError as e:
            error_msg = str(e)
            is_cyclic = "Cyclic references detected" in error_msg

            return SubsumptionResult(
                is_compatible=False,
                error_message=error_msg,
                requires_simulation=is_cyclic,
            )

        except JSoundError as e:
            return SubsumptionResult(is_compatible=False, error_message=str(e))

        except Exception as e:
            return SubsumptionResult(
                is_compatible=False, error_message=f"Unexpected error: {e}"
            )

    def is_compatible(
        self, producer_schema: Dict[str, Any], consumer_schema: Dict[str, Any]
    ) -> bool:
        """
        Quick compatibility check (returns boolean only).

        Args:
            producer_schema: The producer JSON schema
            consumer_schema: The consumer JSON schema

        Returns:
            True if producer ⊆ consumer, False otherwise
        """
        result = self.check_subsumption(producer_schema, consumer_schema)
        return result.is_compatible

    def find_counterexample(
        self, producer_schema: Dict[str, Any], consumer_schema: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find a counterexample if schemas are incompatible.

        Args:
            producer_schema: The producer JSON schema
            consumer_schema: The consumer JSON schema

        Returns:
            A value that satisfies producer but not consumer, or None if compatible
        """
        result = self.check_subsumption(producer_schema, consumer_schema)
        return result.counterexample


# Convenience functions for quick testing
def check_subsumption(
    producer: Dict[str, Any], consumer: Dict[str, Any], **kwargs
) -> bool:
    """
    Quick function to check if producer ⊆ consumer.

    Args:
        producer: Producer schema (more specific)
        consumer: Consumer schema (more general)
        **kwargs: Additional configuration options

    Returns:
        True if producer ⊆ consumer
    """
    api = JSoundAPI(**kwargs)
    return api.is_compatible(producer, consumer)


def find_counterexample(
    producer: Dict[str, Any], consumer: Dict[str, Any], **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Quick function to find a counterexample for incompatible schemas.

    Args:
        producer: Producer schema (more specific)
        consumer: Consumer schema (more general)
        **kwargs: Additional configuration options

    Returns:
        Counterexample or None if compatible
    """
    api = JSoundAPI(**kwargs)
    return api.find_counterexample(producer, consumer)
