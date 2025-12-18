"""Enhanced JSSound API with detailed explanations."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .api import JSoundAPI, SubsumptionResult


@dataclass
class EnhancedSubsumptionResult:
    """Enhanced subsumption result with detailed explanations."""

    is_compatible: bool
    counterexample: Optional[Any] = None
    error_message: Optional[str] = None
    solver_time: float = 0.0
    requires_simulation: bool = False

    # Enhanced fields
    explanation: Optional[str] = None
    failed_constraints: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None

    def __post_init__(self):
        if self.failed_constraints is None:
            self.failed_constraints = []
        if self.recommendations is None:
            self.recommendations = []


class EnhancedJSoundAPI:
    """Enhanced JSSound API with detailed failure explanations."""

    def __init__(self, **kwargs):
        self.base_api = JSoundAPI(**kwargs)

    def check_subsumption(
        self, producer_schema: Dict[str, Any], consumer_schema: Dict[str, Any]
    ) -> EnhancedSubsumptionResult:
        """Check subsumption with enhanced explanations."""

        # Get base result
        base_result = self.base_api.check_subsumption(producer_schema, consumer_schema)

        # Create enhanced result
        enhanced = EnhancedSubsumptionResult(
            is_compatible=base_result.is_compatible,
            counterexample=base_result.counterexample,
            error_message=base_result.error_message,
            solver_time=base_result.solver_time or 0.0,
            requires_simulation=base_result.requires_simulation,
        )

        # Add explanations for incompatible cases
        if not base_result.is_compatible and base_result.counterexample is not None:
            explanation_result = self._generate_explanation(
                producer_schema, consumer_schema, base_result.counterexample
            )
            enhanced.explanation = explanation_result["explanation"]
            enhanced.failed_constraints = explanation_result["failed_constraints"]
            enhanced.recommendations = explanation_result["recommendations"]

        return enhanced

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
        counterexample: List[Any],
        failed_constraints: List[str],
        recommendations: List[str],
    ) -> List[str]:
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
        counterexample: List[Any],
        failed_constraints: List[str],
        recommendations: List[str],
    ) -> List[str]:
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
        counterexample: Dict[str, Any],
        failed_constraints: List[str],
        recommendations: List[str],
    ) -> List[str]:
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

        # Check additionalProperties conflicts
        if consumer.get("additionalProperties") == False:
            consumer_props = set(consumer.get("properties", {}).keys())
            extra_props = set(counterexample.keys()) - consumer_props
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
