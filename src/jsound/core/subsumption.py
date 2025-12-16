"""Core subsumption checking logic."""

import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

from z3 import *
from .json_encoding import JSONEncoder, FiniteKeyUniverse
from .schema_compiler import SchemaCompiler
from .witness import WitnessExtractor
from ..exceptions import SolverTimeoutError, JSoundError


@dataclass
class CheckResult:
    """Result of subsumption checking."""

    is_compatible: bool
    counterexample: Optional[Dict[str, Any]] = None
    solver_time: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class SolverConfig:
    """Configuration for Z3 solver."""

    timeout: int = 30  # seconds
    max_array_len: int = 50
    max_recursion_depth: int = 3


class SubsumptionChecker:
    """Main subsumption checking engine."""

    def __init__(self, config: SolverConfig):
        self.config = config
        self.json_encoder = None
        self.schema_compiler = None
        self.witness_extractor = None

    def check_subsumption(
        self, producer_schema: Dict[str, Any], consumer_schema: Dict[str, Any]
    ) -> CheckResult:
        """Check if producer_schema ⊆ consumer_schema.

        This is done by checking if P ∧ ¬C is satisfiable.
        If SAT, then there exists a counterexample.
        If UNSAT, then P ⊆ C (producer subsumes consumer).
        """
        start_time = time.time()

        try:
            # Setup components
            self._setup_components(producer_schema, consumer_schema)

            # Create Z3 solver
            solver = self._setup_solver()

            # Create JSON variable
            json_sort = self.json_encoder.get_json_sort()
            json_var = Const("x", json_sort)

            # Add mutual exclusion constraint (exactly one type must hold)
            solver.add(
                self.json_encoder.create_mutually_exclusive_constraints(json_var)
            )

            # Encode schemas
            producer_constraint = self.schema_compiler.compile_schema(
                producer_schema, json_var
            )
            consumer_constraint = self.schema_compiler.compile_schema(
                consumer_schema, json_var
            )

            # Add P ∧ ¬C
            solver.add(producer_constraint)
            solver.add(Not(consumer_constraint))

            # Check satisfiability
            result = solver.check()

            solver_time = time.time() - start_time

            if result == sat:
                # Counterexample found - schemas are incompatible
                model = solver.model()
                counterexample = self.witness_extractor.extract_counterexample(model)
                return CheckResult(
                    is_compatible=False,
                    counterexample=counterexample,
                    solver_time=solver_time,
                )
            elif result == unsat:
                # No counterexample - schemas are compatible
                return CheckResult(is_compatible=True, solver_time=solver_time)
            else:  # unknown
                return CheckResult(
                    is_compatible=False,
                    error_message=f"Z3 solver returned unknown after {solver_time:.2f}s",
                    solver_time=solver_time,
                )

        except Exception as e:
            solver_time = time.time() - start_time
            return CheckResult(
                is_compatible=False, error_message=str(e), solver_time=solver_time
            )

    def _setup_components(
        self, producer_schema: Dict[str, Any], consumer_schema: Dict[str, Any]
    ) -> None:
        """Setup JSON encoder, schema compiler, and witness extractor."""

        # Extract finite universes from both schemas
        key_universe = FiniteKeyUniverse()
        key_universe.add_keys_from_schema(producer_schema)
        key_universe.add_keys_from_schema(consumer_schema)

        # Create JSON encoder
        self.json_encoder = JSONEncoder(max_array_len=self.config.max_array_len)

        # Create schema compiler
        self.schema_compiler = SchemaCompiler(self.json_encoder, key_universe)
        self.schema_compiler.max_recursion_depth = self.config.max_recursion_depth

        # Create witness extractor
        self.witness_extractor = WitnessExtractor(self.json_encoder)

    def _setup_solver(self) -> Solver:
        """Setup Z3 solver with configuration."""
        solver = Solver()

        # Set timeout
        solver.set("timeout", self.config.timeout * 1000)  # Z3 expects milliseconds

        # Other solver configurations can go here
        # solver.set("model", True)  # Enable model generation

        return solver
