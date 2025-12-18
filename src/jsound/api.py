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

    # Verification detail fields for --show-verification
    producer_constraints: Optional[str] = None
    consumer_constraints: Optional[str] = None
    verification_formula: Optional[str] = None
    z3_model: Optional[str] = None

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
        capture_verification_details: bool = False,
    ):
        """
        Initialize the JSO API.

        Args:
            timeout: Z3 solver timeout in seconds
            max_array_length: Maximum array length for bounds
            ref_resolution_strategy: 'unfold' (acyclic only) or 'simulation' (future)
            explanations: Enable detailed explanations for incompatibility (default: True)
            capture_verification_details: Enable capture of detailed Z3 constraints for debugging
        """
        self.config = SolverConfig(
            timeout=timeout,
            max_array_len=max_array_length,
            ref_resolution_strategy=ref_resolution_strategy,
            capture_verification_details=capture_verification_details,
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
                # Transfer verification details if captured
                producer_constraints=getattr(result, "producer_constraints", None),
                consumer_constraints=getattr(result, "consumer_constraints", None),
                verification_formula=getattr(result, "verification_formula", None),
                z3_model=getattr(result, "z3_model", None),
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

        # Check for oneOf/anyOf specific failures
        oneof_explanation = self._analyze_oneof_failure(
            producer, consumer, counterexample, failed_constraints, recommendations
        )
        if oneof_explanation:
            explanation_parts.extend(oneof_explanation)
        elif not explanation_parts:
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

        # Check uniqueItems constraint violations
        if consumer.get("uniqueItems") is True and not producer.get("uniqueItems"):
            duplicates = self._find_duplicate_elements(counterexample)
            if duplicates:
                for element, indices in duplicates.items():
                    indices_str = ", ".join(map(str, indices))
                    explanation_parts.append(
                        f"Array contains duplicate elements at indices {indices_str}: {repr(element)}"
                    )
                failed_constraints.append("uniqueItems:true")
                recommendations.append(
                    "Add uniqueItems: true to producer schema or ensure array elements are unique"
                )

        return explanation_parts

    def _find_duplicate_elements(self, array: list) -> dict:
        """Find duplicate elements in array and return their indices.

        Returns:
            Dict mapping duplicate elements to list of their indices
        """
        element_indices = {}
        duplicates = {}

        for i, element in enumerate(array):
            # Convert element to a hashable type for tracking
            try:
                key = (
                    element
                    if isinstance(element, (str, int, float, bool))
                    else str(element)
                )
            except:
                key = str(element)

            if key not in element_indices:
                element_indices[key] = []
            element_indices[key].append(i)

        # Find elements that appear more than once
        for element, indices in element_indices.items():
            if len(indices) > 1:
                duplicates[element] = indices

        return duplicates

    def _analyze_oneof_failure(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: Any,
        failed_constraints: list,
        recommendations: list,
    ) -> list:
        """Analyze oneOf constraint failures."""
        explanation_parts = []

        # Check if either schema uses oneOf
        producer_oneof = producer.get("oneOf")
        consumer_oneof = consumer.get("oneOf")

        if not (producer_oneof or consumer_oneof):
            return explanation_parts

        if producer_oneof and consumer_oneof:
            # Both use oneOf - analyze which options match
            producer_matches = self._find_matching_schemas(
                counterexample, producer_oneof
            )
            consumer_matches = self._find_matching_schemas(
                counterexample, consumer_oneof
            )

            if len(producer_matches) == 1 and len(consumer_matches) == 0:
                explanation_parts.append(
                    f"Value matches producer oneOf option {producer_matches[0]} but no consumer oneOf options"
                )
                failed_constraints.append(f"oneOf:no_consumer_match")
                recommendations.append(
                    "Add compatible schema option to consumer oneOf or modify producer oneOf"
                )

            elif len(producer_matches) == 1 and len(consumer_matches) > 1:
                explanation_parts.append(
                    f"Value matches producer oneOf option {producer_matches[0]} but multiple consumer oneOf options {consumer_matches} (violates exactly-one requirement)"
                )
                failed_constraints.append(f"oneOf:multiple_consumer_matches")
                recommendations.append(
                    "Make consumer oneOf options more specific to avoid multiple matches"
                )

            elif len(producer_matches) > 1:
                explanation_parts.append(
                    f"Value matches multiple producer oneOf options {producer_matches} (violates exactly-one requirement)"
                )
                failed_constraints.append(f"oneOf:multiple_producer_matches")
                recommendations.append(
                    "Make producer oneOf options more specific to avoid multiple matches"
                )

        elif consumer_oneof:
            # Only consumer uses oneOf
            consumer_matches = self._find_matching_schemas(
                counterexample, consumer_oneof
            )
            if len(consumer_matches) == 0:
                explanation_parts.append(
                    f"Value doesn't match any consumer oneOf options"
                )
                failed_constraints.append("oneOf:no_match")
                recommendations.append(
                    "Add schema option to consumer oneOf that covers producer values"
                )
            elif len(consumer_matches) > 1:
                explanation_parts.append(
                    f"Value matches multiple consumer oneOf options {consumer_matches} (violates exactly-one requirement)"
                )
                failed_constraints.append("oneOf:multiple_matches")
                recommendations.append(
                    "Make consumer oneOf options more specific to avoid multiple matches"
                )

        return explanation_parts

    def _find_matching_schemas(self, value: Any, schemas: list) -> list:
        """Find which schemas in a oneOf/anyOf list match the given value."""
        matches = []
        for i, schema in enumerate(schemas):
            if self._element_satisfies_schema(value, schema):
                matches.append(i)
        return matches

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

        # Check patternProperties conflicts
        self._analyze_pattern_properties_failures(
            producer,
            consumer,
            counterexample,
            failed_constraints,
            recommendations,
            explanation_parts,
        )

        # Check uniqueItems conflicts for object properties that are arrays
        self._analyze_object_unique_items_failures(
            producer,
            consumer,
            counterexample,
            failed_constraints,
            recommendations,
            explanation_parts,
        )

        # Check dependency violations
        self._analyze_dependency_failures(
            producer,
            consumer,
            counterexample,
            failed_constraints,
            recommendations,
            explanation_parts,
        )

        # Check const/enum violations
        self._analyze_const_enum_failures(
            producer,
            consumer,
            counterexample,
            failed_constraints,
            recommendations,
            explanation_parts,
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

    def _analyze_pattern_properties_failures(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: dict,
        failed_constraints: list,
        recommendations: list,
        explanation_parts: list,
    ) -> None:
        """Analyze patternProperties schema failures."""
        import re

        producer_patterns = producer.get("patternProperties", {})
        consumer_patterns = consumer.get("patternProperties", {})

        # Check each property in the counterexample
        for prop_name, prop_value in counterexample.items():
            # Find patterns that match this property name
            producer_matching_patterns = []
            consumer_matching_patterns = []

            for pattern in producer_patterns:
                try:
                    if re.match(pattern, prop_name):
                        producer_matching_patterns.append(pattern)
                except re.error:
                    pass

            for pattern in consumer_patterns:
                try:
                    if re.match(pattern, prop_name):
                        consumer_matching_patterns.append(pattern)
                except re.error:
                    pass

            # Check for type mismatches between matching patterns
            for consumer_pattern in consumer_matching_patterns:
                consumer_schema = consumer_patterns[consumer_pattern]

                # Check if this property value violates the consumer pattern schema
                if not self._element_satisfies_schema(prop_value, consumer_schema):
                    # Find if there's a conflicting producer pattern
                    for producer_pattern in producer_matching_patterns:
                        producer_schema = producer_patterns[producer_pattern]

                        if self._element_satisfies_schema(prop_value, producer_schema):
                            # Found conflict: satisfies producer pattern but violates consumer pattern
                            producer_type = producer_schema.get("type", "any")
                            consumer_type = consumer_schema.get("type", "any")

                            explanation_parts.append(
                                f"Property '{prop_name}' matches pattern '{consumer_pattern}' but type mismatch: "
                                f"producer pattern expects '{producer_type}', consumer pattern requires '{consumer_type}'"
                            )
                            failed_constraints.append(
                                f"patternProperties:{consumer_pattern}:{producer_type}→{consumer_type}"
                            )
                            recommendations.append(
                                f"Change producer pattern '{producer_pattern}' type from '{producer_type}' to '{consumer_type}'"
                            )
                            break

    def _analyze_object_unique_items_failures(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: dict,
        failed_constraints: list,
        recommendations: list,
        explanation_parts: list,
    ) -> None:
        """Analyze uniqueItems failures in object properties that are arrays."""
        producer_props = producer.get("properties", {})
        consumer_props = consumer.get("properties", {})

        # Check each property in the counterexample
        for prop_name, prop_value in counterexample.items():
            if not isinstance(prop_value, list):
                continue  # Skip non-array properties

            # Check if this property has uniqueItems constraint in consumer but not producer
            consumer_prop = consumer_props.get(prop_name, {})
            producer_prop = producer_props.get(prop_name, {})

            consumer_unique = consumer_prop.get("uniqueItems") is True
            producer_unique = producer_prop.get("uniqueItems") is True

            if consumer_unique and not producer_unique:
                # Consumer requires unique items but producer allows duplicates
                duplicates = self._find_duplicate_elements(prop_value)
                if duplicates:
                    for element, indices in duplicates.items():
                        indices_str = ", ".join(map(str, indices))
                        explanation_parts.append(
                            f"Property '{prop_name}' contains duplicate elements at indices {indices_str}: {repr(element)}"
                        )
                    failed_constraints.append(f"uniqueItems:{prop_name}:true")
                    recommendations.append(
                        f"Add uniqueItems: true to producer property '{prop_name}' or ensure array elements are unique"
                    )

    def _analyze_dependency_failures(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: dict,
        failed_constraints: list,
        recommendations: list,
        explanation_parts: list,
    ) -> None:
        """Analyze dependency violations in the counterexample."""

        # Check dependentRequired violations
        consumer_dep_req = consumer.get("dependentRequired", {})
        if consumer_dep_req:
            for trigger_prop, required_deps in consumer_dep_req.items():
                if trigger_prop in counterexample:
                    # Property exists, check if all dependencies are present
                    missing_deps = []
                    for dep_prop in required_deps:
                        if dep_prop not in counterexample:
                            missing_deps.append(dep_prop)

                    if missing_deps:
                        missing_str = ", ".join(f"'{dep}'" for dep in missing_deps)
                        explanation_parts.append(
                            f"Property '{trigger_prop}' requires {missing_str} but they are missing"
                        )
                        failed_constraints.append(
                            f"dependentRequired:{trigger_prop}→{','.join(missing_deps)}"
                        )
                        recommendations.append(
                            f"Add properties {missing_str} to producer schema when '{trigger_prop}' is present"
                        )

        # Check dependentSchemas violations
        consumer_dep_schemas = consumer.get("dependentSchemas", {})
        if consumer_dep_schemas:
            for trigger_prop, dependent_schema in consumer_dep_schemas.items():
                if trigger_prop in counterexample:
                    # Property exists, check if object satisfies the dependent schema
                    if not self._object_satisfies_schema(
                        counterexample, dependent_schema
                    ):
                        schema_desc = self._describe_schema_constraint(dependent_schema)
                        explanation_parts.append(
                            f"Property '{trigger_prop}' requires object to satisfy schema {schema_desc}"
                        )
                        failed_constraints.append(f"dependentSchemas:{trigger_prop}")
                        recommendations.append(
                            f"Ensure producer satisfies dependent schema when '{trigger_prop}' is present"
                        )

        # Check legacy dependencies (Draft 7 format)
        consumer_deps = consumer.get("dependencies", {})
        if consumer_deps:
            for trigger_prop, dependency in consumer_deps.items():
                if trigger_prop in counterexample:
                    if isinstance(dependency, list):
                        # Property dependency (like dependentRequired)
                        missing_deps = [
                            dep for dep in dependency if dep not in counterexample
                        ]
                        if missing_deps:
                            missing_str = ", ".join(f"'{dep}'" for dep in missing_deps)
                            explanation_parts.append(
                                f"Property '{trigger_prop}' requires {missing_str} but they are missing"
                            )
                            failed_constraints.append(
                                f"dependencies:{trigger_prop}→{','.join(missing_deps)}"
                            )
                            recommendations.append(
                                f"Add properties {missing_str} to producer schema when '{trigger_prop}' is present"
                            )
                    elif isinstance(dependency, dict):
                        # Schema dependency (like dependentSchemas)
                        if not self._object_satisfies_schema(
                            counterexample, dependency
                        ):
                            schema_desc = self._describe_schema_constraint(dependency)
                            explanation_parts.append(
                                f"Property '{trigger_prop}' requires object to satisfy dependency schema {schema_desc}"
                            )
                            failed_constraints.append(f"dependencies:{trigger_prop}")
                            recommendations.append(
                                f"Ensure producer satisfies dependency schema when '{trigger_prop}' is present"
                            )

    def _analyze_const_enum_failures(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        counterexample: Any,
        failed_constraints: list,
        recommendations: list,
        explanation_parts: list,
    ) -> None:
        """Analyze const and enum constraint violations."""

        # Check top-level const/enum mismatches for primitive values
        if not isinstance(counterexample, dict):
            self._check_const_enum_violation(
                producer,
                consumer,
                counterexample,
                failed_constraints,
                recommendations,
                explanation_parts,
            )
            return
            return

        # Check top-level const/enum mismatches for objects
        self._check_const_enum_violation(
            producer,
            consumer,
            counterexample,
            failed_constraints,
            recommendations,
            explanation_parts,
        )

        # Check property-level const/enum mismatches for objects
        producer_props = producer.get("properties", {})
        consumer_props = consumer.get("properties", {})

        for prop_name, prop_value in counterexample.items():
            if prop_name in consumer_props:
                consumer_prop_schema = consumer_props[prop_name]
                producer_prop_schema = producer_props.get(prop_name, {})

                self._check_const_enum_violation(
                    producer_prop_schema,
                    consumer_prop_schema,
                    prop_value,
                    failed_constraints,
                    recommendations,
                    explanation_parts,
                    property_name=prop_name,
                )

        # Check property-level const/enum mismatches for objects
        if isinstance(counterexample, dict):
            producer_props = producer.get("properties", {})
            consumer_props = consumer.get("properties", {})

            for prop_name, prop_value in counterexample.items():
                if prop_name in consumer_props:
                    consumer_prop_schema = consumer_props[prop_name]
                    producer_prop_schema = producer_props.get(prop_name, {})

                    self._check_const_enum_violation(
                        producer_prop_schema,
                        consumer_prop_schema,
                        prop_value,
                        failed_constraints,
                        recommendations,
                        explanation_parts,
                        property_name=prop_name,
                    )

    def _check_const_enum_violation(
        self,
        producer: Dict[str, Any],
        consumer: Dict[str, Any],
        value: Any,
        failed_constraints: list,
        recommendations: list,
        explanation_parts: list,
        property_name: Optional[str] = None,
    ) -> None:
        """Check for const/enum constraint violations."""

        prefix = f"Property '{property_name}' " if property_name else ""
        context = property_name or "root"

        # Consumer has const constraint
        if "const" in consumer:
            consumer_const = consumer["const"]

            if "const" in producer:
                producer_const = producer["const"]
                if producer_const != consumer_const:
                    explanation_parts.append(
                        f"{prefix}const mismatch: producer requires '{producer_const}', consumer requires '{consumer_const}'"
                    )
                    failed_constraints.append(
                        f"const:{context}:{producer_const}→{consumer_const}"
                    )
                    recommendations.append(
                        f"Change {prefix.lower() if prefix else 'schema '}const from '{producer_const}' to '{consumer_const}'"
                    )
            elif "enum" in producer:
                producer_enum = producer["enum"]
                if consumer_const not in producer_enum:
                    explanation_parts.append(
                        f"{prefix}const/enum mismatch: producer enum {producer_enum} doesn't include consumer const '{consumer_const}'"
                    )
                    failed_constraints.append(f"const_enum_mismatch:{context}")
                    recommendations.append(
                        f"Add '{consumer_const}' to {prefix.lower() if prefix else 'schema '}enum or change to const"
                    )
            elif value != consumer_const:
                explanation_parts.append(
                    f"{prefix}violates const constraint: value '{value}' not allowed, consumer requires '{consumer_const}'"
                )
                failed_constraints.append(f"const_violation:{context}")
                recommendations.append(
                    f"Add {prefix.lower() if prefix else 'schema '}const constraint '{consumer_const}' to producer"
                )

        # Consumer has enum constraint
        elif "enum" in consumer:
            consumer_enum = consumer["enum"]

            if "const" in producer:
                producer_const = producer["const"]
                if producer_const not in consumer_enum:
                    explanation_parts.append(
                        f"{prefix}const/enum mismatch: producer const '{producer_const}' not in consumer enum {consumer_enum}"
                    )
                    failed_constraints.append(f"const_enum_mismatch:{context}")
                    recommendations.append(
                        f"Change {prefix.lower() if prefix else 'schema '}const '{producer_const}' to one of {consumer_enum}"
                    )
            elif "enum" in producer:
                producer_enum = producer["enum"]
                invalid_values = [v for v in producer_enum if v not in consumer_enum]
                if invalid_values:
                    explanation_parts.append(
                        f"{prefix}enum mismatch: producer allows {invalid_values} not in consumer enum {consumer_enum}"
                    )
                    failed_constraints.append(f"enum_mismatch:{context}")
                    recommendations.append(
                        f"Remove {invalid_values} from {prefix.lower() if prefix else 'schema '}enum or expand consumer enum"
                    )
            elif value not in consumer_enum:
                explanation_parts.append(
                    f"{prefix}violates enum constraint: value '{value}' not in allowed values {consumer_enum}"
                )
                failed_constraints.append(f"enum_violation:{context}")
                recommendations.append(
                    f"Add {prefix.lower() if prefix else 'schema '}enum constraint {consumer_enum} to producer"
                )

    def _object_satisfies_schema(self, obj: dict, schema: Dict[str, Any]) -> bool:
        """Simple check if object satisfies schema constraints."""
        # Check required properties
        required = schema.get("required", [])
        for prop in required:
            if prop not in obj:
                return False

        # Check property schemas
        properties = schema.get("properties", {})
        for prop_name, prop_value in obj.items():
            if prop_name in properties:
                if not self._element_satisfies_schema(
                    prop_value, properties[prop_name]
                ):
                    return False

        # Basic checks - can be extended as needed
        return True

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
