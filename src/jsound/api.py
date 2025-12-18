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
    """Result of a subsumption check with optional detailed explanations."""

    is_compatible: bool
    counterexample: Optional[Any] = None
    error_message: Optional[str] = None
    solver_time: Optional[float] = None
    requires_simulation: bool = False

    # Enhanced explanation fields (Sprint 2 integration)
    explanation: Optional[str] = None
    failed_constraints: Optional[list] = None
    recommendations: Optional[list] = None

    def has_explanations(self) -> bool:
        """Check if detailed explanations are available."""
        return self.explanation is not None or bool(self.failed_constraints)

    def get_detailed_explanation(self) -> str:
        """Get a formatted detailed explanation."""
        if not self.has_explanations():
            return "No detailed explanation available."

        parts = []
        if self.explanation:
            parts.append(f"Explanation: {self.explanation}")

        if self.failed_constraints:
            parts.append(f"Failed constraints: {', '.join(self.failed_constraints)}")

        if self.recommendations:
            recommendations_text = "\n".join(
                f"  • {rec}" for rec in self.recommendations
            )
            parts.append(f"Recommendations:\n{recommendations_text}")

        return "\n".join(parts)


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
        explanations: bool = True,
    ):
        """
        Initialize the JSO API.

        Args:
            timeout: Z3 solver timeout in seconds
            max_array_length: Maximum array length for bounds
            ref_resolution_strategy: 'unfold' (acyclic only) or 'simulation' (future)
            explanations: Enable detailed explanations for incompatibility (default: True)
        """
        self.config = SolverConfig(
            timeout=timeout,
            max_array_len=max_array_length,
            ref_resolution_strategy=ref_resolution_strategy,
        )
        self.explanations_enabled = explanations

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
            subsumption_result = SubsumptionResult(
                is_compatible=result.is_compatible,
                counterexample=result.counterexample,
                solver_time=result.solver_time,
                error_message=result.error_message,
            )

            # Generate explanations if enabled and incompatible
            if (
                self.explanations_enabled
                and not result.is_compatible
                and result.counterexample is not None
            ):
                explanation_result = self._generate_explanation(
                    producer_schema, consumer_schema, result.counterexample
                )
                subsumption_result.explanation = explanation_result["explanation"]
                subsumption_result.failed_constraints = explanation_result[
                    "failed_constraints"
                ]
                subsumption_result.recommendations = explanation_result[
                    "recommendations"
                ]

            return subsumption_result

        except UnsupportedFeatureError as e:
            error_msg = str(e)
            is_cyclic = "Cyclic references detected" in error_msg

            return SubsumptionResult(
                is_compatible=False,
                error_message=str(e),
                requires_simulation=is_cyclic,
            )

        except JSoundError as e:
            return SubsumptionResult(is_compatible=False, error_message=str(e))

        except Exception as e:
            return SubsumptionResult(
                is_compatible=False, error_message=f"Unexpected error: {e}"
            )

    def _generate_explanation(
        self, producer: Dict[str, Any], consumer: Dict[str, Any], counterexample: Any
    ) -> Dict[str, Any]:
        """Generate explanation using schema pattern analysis."""

        failed_constraints = []
        recommendations = []
        explanation_parts = []

        # Analyze counterexample type
        if isinstance(counterexample, list):
            explanation_parts.extend(
                self._analyze_array_failure(
                    producer,
                    consumer,
                    counterexample,
                    failed_constraints,
                    recommendations,
                )
            )
        elif isinstance(counterexample, dict):
            explanation_parts.extend(
                self._analyze_object_failure(
                    producer,
                    consumer,
                    counterexample,
                    failed_constraints,
                    recommendations,
                )
            )
        else:
            explanation_parts.append(
                f"Value {counterexample} satisfies producer but violates consumer"
            )

        explanation = (
            " | ".join(explanation_parts)
            if explanation_parts
            else "Incompatibility detected but specific cause unclear"
        )

        return {
            "explanation": explanation,
            "failed_constraints": failed_constraints,
            "recommendations": recommendations,
        }

    def _analyze_array_failure(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: list,
        failed_constraints: list,
        recommendations: list,
    ) -> list:
        """Analyze array schema failures."""
        explanation_parts = []

        # Check contains constraint failures
        if "contains" in consumer:
            contains_schema = consumer["contains"]
            explanation_parts.extend(
                self._analyze_contains_failure(
                    producer,
                    contains_schema,
                    counterexample,
                    failed_constraints,
                    recommendations,
                )
            )

        # Check items constraint mismatches
        if "items" in producer and "items" in consumer:
            prod_items = producer["items"]
            cons_items = consumer["items"]
            if prod_items != cons_items:
                explanation_parts.append(
                    f"Array item constraints differ: producer allows {prod_items}, consumer requires {cons_items}"
                )
                failed_constraints.append("items_mismatch")

        # Check length constraint mismatches
        if "minItems" in consumer:
            min_items = consumer["minItems"]
            if len(counterexample) < min_items:
                explanation_parts.append(
                    f"Array too short: has {len(counterexample)} items, needs ≥{min_items}"
                )
                failed_constraints.append(f"minItems:{min_items}")
                recommendations.append(f"Add minItems: {min_items} to producer schema")

        return explanation_parts

    def _analyze_contains_failure(
        self,
        producer: Dict[str, Any],
        contains_schema: Dict[str, Any],
        counterexample: list,
        failed_constraints: list,
        recommendations: list,
    ) -> list:
        """Analyze contains constraint failures."""
        explanation_parts = []

        # Check if any element satisfies contains constraint
        satisfying_elements = []
        for elem in counterexample:
            if self._element_satisfies_schema(elem, contains_schema):
                satisfying_elements.append(elem)

        if not satisfying_elements:
            # No elements satisfy contains constraint
            constraint_desc = self._describe_schema_constraint(contains_schema)
            explanation_parts.append(
                f"Array contains no elements satisfying {constraint_desc}"
            )
            failed_constraints.append(f"contains:{constraint_desc}")

            # Generate recommendations based on producer items constraints
            if "items" in producer:
                items_schema = producer["items"]
                rec = self._recommend_contains_fix(items_schema, contains_schema)
                if rec:
                    recommendations.append(rec)

        return explanation_parts

    def _analyze_object_failure(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: dict,
        failed_constraints: list,
        recommendations: list,
    ) -> list:
        """Analyze object schema failures."""
        explanation_parts = []

        # Check required property mismatches
        if "required" in consumer:
            for required_prop in consumer["required"]:
                if (
                    required_prop not in counterexample
                    or counterexample[required_prop] is None
                ):
                    explanation_parts.append(
                        f"Missing required property '{required_prop}'"
                    )
                    failed_constraints.append(f"required:{required_prop}")
                    recommendations.append(
                        f"Add '{required_prop}' to producer's required properties"
                    )

        # Check format constraint mismatches
        producer_props = producer.get("properties", {})
        consumer_props = consumer.get("properties", {})

        for prop_name in counterexample.keys():
            if prop_name in producer_props and prop_name in consumer_props:
                prod_prop = producer_props[prop_name]
                cons_prop = consumer_props[prop_name]

                # Check format mismatches
                prod_format = prod_prop.get("format")
                cons_format = cons_prop.get("format")

                if prod_format and cons_format and prod_format != cons_format:
                    explanation_parts.append(
                        f"Property '{prop_name}' format mismatch: producer has '{prod_format}', consumer requires '{cons_format}'"
                    )
                    failed_constraints.append(
                        f"format:{prop_name}:{prod_format}→{cons_format}"
                    )
                    recommendations.append(
                        f"Change producer property '{prop_name}' format from '{prod_format}' to '{cons_format}'"
                    )
                elif cons_format and not prod_format:
                    explanation_parts.append(
                        f"Property '{prop_name}' missing format constraint: consumer requires '{cons_format}'"
                    )
                    failed_constraints.append(
                        f"format:{prop_name}:missing→{cons_format}"
                    )
                    recommendations.append(
                        f"Add format: '{cons_format}' to producer property '{prop_name}'"
                    )

        # Check additionalProperties conflicts
        if consumer.get("additionalProperties") == False:
            consumer_props_set = set(consumer.get("properties", {}).keys())
            extra_props = set(counterexample.keys()) - consumer_props_set
            if extra_props:
                explanation_parts.append(f"Extra properties not allowed: {extra_props}")
                failed_constraints.append(f"additionalProperties:false")
                recommendations.append(
                    "Remove additionalProperties: false from consumer or add properties to consumer schema"
                )

        return explanation_parts

    def _element_satisfies_schema(self, element: Any, schema: Dict[str, Any]) -> bool:
        """Simple check if element satisfies schema (basic implementation)."""

        # Type check
        if "type" in schema:
            schema_type = schema["type"]
            if schema_type == "string" and not isinstance(element, str):
                return False
            elif schema_type == "number" and not isinstance(element, (int, float)):
                return False
            elif schema_type == "integer" and not isinstance(element, int):
                return False
            elif schema_type == "boolean" and not isinstance(element, bool):
                return False
            elif schema_type == "array" and not isinstance(element, list):
                return False
            elif schema_type == "object" and not isinstance(element, dict):
                return False

        # Numeric constraints
        if isinstance(element, (int, float)):
            if "minimum" in schema and element < schema["minimum"]:
                return False
            if "maximum" in schema and element > schema["maximum"]:
                return False
            if "exclusiveMinimum" in schema and element <= schema["exclusiveMinimum"]:
                return False
            if "exclusiveMaximum" in schema and element >= schema["exclusiveMaximum"]:
                return False

        # String constraints
        if isinstance(element, str):
            if "minLength" in schema and len(element) < schema["minLength"]:
                return False
            if "maxLength" in schema and len(element) > schema["maxLength"]:
                return False

        # Const constraint
        if "const" in schema and element != schema["const"]:
            return False

        return True

    def _describe_schema_constraint(self, schema: Dict[str, Any]) -> str:
        """Generate human-readable description of schema constraint."""
        parts = []

        if "type" in schema:
            parts.append(f"type: {schema['type']}")

        if "minimum" in schema:
            parts.append(f"≥{schema['minimum']}")

        if "maximum" in schema:
            parts.append(f"≤{schema['maximum']}")

        if "minLength" in schema:
            parts.append(f"length ≥{schema['minLength']}")

        if "const" in schema:
            parts.append(f"const: {schema['const']}")

        if "format" in schema:
            parts.append(f"format: {schema['format']}")

        return "{" + ", ".join(parts) + "}" if parts else "any"

    def _recommend_contains_fix(
        self, items_schema: Dict[str, Any], contains_schema: Dict[str, Any]
    ) -> Optional[str]:
        """Recommend how to fix contains constraint failures."""

        # If contains requires minimum but items allows lower
        if (
            "minimum" in contains_schema
            and "minimum" in items_schema
            and items_schema["minimum"] < contains_schema["minimum"]
        ):
            return f"Change producer items minimum from {items_schema['minimum']} to {contains_schema['minimum']}"

        # If contains requires specific type but items allows different types
        if "type" in contains_schema and "anyOf" in items_schema:
            return f"Ensure producer guarantees at least one {contains_schema['type']} element"

        return None

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
