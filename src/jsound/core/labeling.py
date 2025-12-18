"""Constraint labeling system for detailed subsumption explanations."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from z3 import BoolRef, Bool, ModelRef, is_true, BoolVal


@dataclass
class LabeledCompilation:
    """Result of schema compilation with constraint labels."""

    formula: BoolRef
    labels: Dict[str, BoolRef]
    schema_path: str = ""


@dataclass
class LabelEvaluation:
    """Result of evaluating labels in a Z3 model."""

    label: str
    is_satisfied: bool
    schema_path: str
    constraint_type: str
    value: Any = None


class ConstraintLabeler:
    """Creates labeled Z3 constraints for explanation generation."""

    def __init__(self):
        self.label_counter = 0

    def create_label(
        self, path: str, constraint_type: str, labels: Dict[str, BoolRef]
    ) -> BoolRef:
        """Create a new labeled constraint.

        Args:
            path: JSON path like "/properties/name" or "/items/minimum"
            constraint_type: Type like "type", "minimum", "pattern", "contains"
            labels: Dictionary to store the label mapping

        Returns:
            Z3 BoolRef that can be equated to a constraint
        """
        self.label_counter += 1
        label_name = f"{path}:{constraint_type}:{self.label_counter}"
        bool_var = Bool(label_name)
        labels[label_name] = bool_var
        return bool_var

    def label_constraint(
        self,
        path: str,
        constraint_type: str,
        constraint: BoolRef,
        labels: Dict[str, BoolRef],
    ) -> BoolRef:
        """Create a labeled constraint.

        Args:
            path: JSON path of the constraint
            constraint_type: Type of constraint
            constraint: The Z3 constraint to label
            labels: Dictionary to store label mappings

        Returns:
            Z3 constraint: label_var == constraint
        """
        label_var = self.create_label(path, constraint_type, labels)
        return label_var == constraint


class LabelEvaluator:
    """Evaluates constraint labels in Z3 models to generate explanations."""

    def evaluate_labels(
        self,
        model: ModelRef,
        producer_labels: Dict[str, BoolRef],
        consumer_labels: Dict[str, BoolRef],
    ) -> List[LabelEvaluation]:
        """Evaluate all labels in the model to find satisfied/failed constraints."""
        evaluations = []

        # Evaluate producer labels (should all be true in counterexample)
        for label_name, bool_ref in producer_labels.items():
            is_satisfied = is_true(model.eval(bool_ref, model_completion=True))
            path, constraint_type, _ = self._parse_label_name(label_name)

            evaluations.append(
                LabelEvaluation(
                    label=label_name,
                    is_satisfied=is_satisfied,
                    schema_path=path,
                    constraint_type=constraint_type,
                )
            )

        # Evaluate consumer labels (failed ones explain incompatibility)
        for label_name, bool_ref in consumer_labels.items():
            is_satisfied = is_true(model.eval(bool_ref, model_completion=True))
            path, constraint_type, _ = self._parse_label_name(label_name)

            evaluations.append(
                LabelEvaluation(
                    label=label_name,
                    is_satisfied=is_satisfied,
                    schema_path=path,
                    constraint_type=constraint_type,
                )
            )

        return evaluations

    def _parse_label_name(self, label_name: str) -> tuple[str, str, str]:
        """Parse label name into (path, constraint_type, counter).

        Example: "/properties/name:type:1" -> ("/properties/name", "type", "1")
        """
        try:
            parts = label_name.split(":")
            if len(parts) >= 3:
                path = ":".join(parts[:-2])  # Handle paths with colons
                constraint_type = parts[-2]
                counter = parts[-1]
                return path, constraint_type, counter
            else:
                return label_name, "unknown", "0"
        except:
            return label_name, "unknown", "0"


class ExplanationGenerator:
    """Generates human-readable explanations from label evaluations."""

    def generate_explanation(
        self,
        evaluations: List[LabelEvaluation],
        counterexample: Any,
        producer_schema: Dict[str, Any],
        consumer_schema: Dict[str, Any],
    ) -> str:
        """Generate a human-readable explanation of why subsumption failed."""

        # Find failed consumer constraints
        failed_consumer = [
            e for e in evaluations if not e.is_satisfied and "/consumer" in e.label
        ]
        satisfied_producer = [
            e for e in evaluations if e.is_satisfied and "/producer" in e.label
        ]

        if not failed_consumer:
            return (
                "Subsumption failed but no specific constraint violations identified."
            )

        # Generate explanation text
        explanation_parts = []

        # Main explanation
        if counterexample:
            explanation_parts.append(f"Counterexample: {counterexample}")

        # Failed consumer constraints
        for failed in failed_consumer[:3]:  # Show up to 3 main failures
            constraint_desc = self._describe_constraint(failed)
            explanation_parts.append(f"Consumer requires: {constraint_desc}")

        # Relevant producer constraints that allowed the counterexample
        relevant_producer = self._find_relevant_producer_constraints(
            failed_consumer, satisfied_producer
        )
        for prod in relevant_producer[:2]:  # Show up to 2 relevant producer constraints
            constraint_desc = self._describe_constraint(prod)
            explanation_parts.append(f"Producer allows: {constraint_desc}")

        return " | ".join(explanation_parts)

    def _describe_constraint(self, evaluation: LabelEvaluation) -> str:
        """Convert a label evaluation to human-readable description."""
        path = evaluation.schema_path.replace("/producer", "").replace("/consumer", "")
        constraint_type = evaluation.constraint_type

        if constraint_type == "type":
            return f"type constraint at {path}"
        elif constraint_type == "minimum":
            return f"minimum value constraint at {path}"
        elif constraint_type == "maximum":
            return f"maximum value constraint at {path}"
        elif constraint_type == "contains":
            return f"array contains constraint at {path}"
        elif constraint_type == "pattern":
            return f"string pattern constraint at {path}"
        elif constraint_type == "format":
            return f"string format constraint at {path}"
        elif constraint_type == "required":
            return f"required property constraint at {path}"
        else:
            return f"{constraint_type} constraint at {path}"

    def _find_relevant_producer_constraints(
        self,
        failed_consumer: List[LabelEvaluation],
        satisfied_producer: List[LabelEvaluation],
    ) -> List[LabelEvaluation]:
        """Find producer constraints that are relevant to consumer failures."""
        relevant = []

        # Simple heuristic: find producer constraints with similar paths or constraint types
        for failed in failed_consumer:
            for prod in satisfied_producer:
                if (
                    failed.constraint_type == prod.constraint_type
                    or failed.schema_path.split("/")[-1]
                    == prod.schema_path.split("/")[-1]
                ):
                    if prod not in relevant:
                        relevant.append(prod)

        return relevant


# Helper function for backward compatibility
def label(
    path: str, constraint_type: str, constraint: BoolRef, labels: Dict[str, BoolRef]
) -> BoolRef:
    """Create a labeled constraint (convenience function)."""
    labeler = ConstraintLabeler()
    return labeler.label_constraint(path, constraint_type, constraint, labels)
