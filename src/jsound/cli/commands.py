"""CLI commands for jsound."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from ..api import JSoundAPI, SubsumptionResult
from ..core.subsumption import SubsumptionChecker, SolverConfig, CheckResult
from ..exceptions import JSoundError, UnsupportedFeatureError

app = typer.Typer()
console = Console()


@app.command()
def check(
    producer_schema_file: Path = typer.Argument(
        ..., help="Path to producer JSON schema file"
    ),
    consumer_schema_file: Path = typer.Argument(
        ..., help="Path to consumer JSON schema file"
    ),
    max_array_length: int = typer.Option(
        50, "--max-array-length", help="Maximum array length for bounds"
    ),
    max_recursion_depth: int = typer.Option(
        3,
        "--max-recursion-depth",
        help="Maximum $ref unrolling depth (deprecated - use ref-resolution-strategy)",
    ),
    ref_resolution_strategy: str = typer.Option(
        "unfold",
        "--ref-resolution-strategy",
        help="Strategy for $ref: 'unfold' (acyclic only) or 'simulation' (supports cycles)",
    ),
    timeout: int = typer.Option(30, "--timeout", help="Z3 solver timeout in seconds"),
    output_format: str = typer.Option(
        "pretty", "--output-format", help="Output format: json, pretty, or minimal"
    ),
    counterexample_file: Optional[Path] = typer.Option(
        None, "--counterexample-file", help="Save counterexample to file"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output"),
    explanations: bool = typer.Option(
        True,
        "--explanations/--no-explanations",
        help="Show detailed explanations for incompatibility",
    ),
    show_verification: bool = typer.Option(
        False,
        "--show-verification",
        help="Show detailed verification conditions and Z3 constraints",
    ),
) -> None:
    """Check if producer schema subsumes consumer schema."""

    try:
        # Load schemas
        producer_schema = load_schema(producer_schema_file)
        consumer_schema = load_schema(consumer_schema_file)

        if verbose:
            console.print(
                f"[blue]Loaded producer schema from {producer_schema_file}[/blue]"
            )
            console.print(
                f"[blue]Loaded consumer schema from {consumer_schema_file}[/blue]"
            )

        # Setup configuration
        config = SolverConfig(
            timeout=timeout,
            max_array_len=max_array_length,
            max_recursion_depth=max_recursion_depth,
            ref_resolution_strategy=ref_resolution_strategy,
            capture_verification_details=show_verification,
        )

        # Perform subsumption check
        # Use enhanced API for better explanations
        api = JSoundAPI(
            timeout=timeout,
            max_array_length=max_array_length,
            ref_resolution_strategy=ref_resolution_strategy,
            explanations=explanations,
            capture_verification_details=show_verification,
        )

        if verbose:
            console.print("[blue]Starting subsumption check...[/blue]")

        result = api.check_subsumption(producer_schema, consumer_schema)

        # Handle output
        if output_format == "json":
            output_json(result)
        elif output_format == "minimal":
            output_minimal(result)
        else:  # pretty
            output_pretty(result, verbose, show_verification)

        # Save counterexample if requested
        if counterexample_file and result.counterexample:
            save_counterexample(result.counterexample, counterexample_file)
            if verbose:
                console.print(
                    f"[blue]Counterexample saved to {counterexample_file}[/blue]"
                )

        # Set exit code
        sys.exit(0 if result.is_compatible else 1)

    except UnsupportedFeatureError as e:
        error_msg = str(e)
        if "Cyclic references detected" in error_msg:
            console.print(f"[red]❌ Cyclic references detected![/red]")
            console.print(f"[yellow]{e}[/yellow]")
            console.print(
                f"[blue]💡 Try again with --ref-resolution-strategy=simulation[/blue]"
            )
        else:
            console.print(f"[red]Error: Unsupported feature[/red]")
            console.print(f"[red]{e}[/red]")
        sys.exit(2)

    except JSoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(2)

    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(2)


def load_schema(schema_file: Path) -> dict:
    """Load and validate JSON schema from file."""
    try:
        with open(schema_file, "r") as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError:
        raise JSoundError(f"Schema file not found: {schema_file}")
    except json.JSONDecodeError as e:
        raise JSoundError(f"Invalid JSON in schema file {schema_file}: {e}")


def output_json(result: SubsumptionResult) -> None:
    """Output result in JSON format."""
    output = {
        "compatible": result.is_compatible,
        "counterexample": result.counterexample,
        "solver_time": result.solver_time,
    }
    if result.error_message:
        output["error"] = result.error_message
    print(json.dumps(output, indent=2))


def output_minimal(result: SubsumptionResult) -> None:
    """Output result in minimal format."""
    if result.is_compatible:
        print("compatible")
    else:
        print("incompatible")
        if result.counterexample:
            print(json.dumps(result.counterexample))


def output_pretty(
    result: SubsumptionResult, verbose: bool = False, show_verification: bool = False
) -> None:
    """Output result in pretty format."""

    # Show verification details if requested
    if show_verification:
        rprint("\n[bold blue]🔍 Verification Process[/bold blue]")
        rprint("[dim]Checking if Producer schema ⊆ Consumer schema[/dim]")
        rprint("[dim]This means: ∀x. Producer(x) → Consumer(x)[/dim]")
        rprint("[dim]We check satisfiability of: Producer(x) ∧ ¬Consumer(x)[/dim]")

        if hasattr(result, "producer_constraints") and result.producer_constraints:
            rprint(f"\n[cyan]Producer constraints (P):[/cyan]")
            rprint(f"[dim]{result.producer_constraints}[/dim]")
            human_p = _explain_constraint(result.producer_constraints)
            if human_p:
                rprint(f"[dim]→ {human_p}[/dim]")

        if hasattr(result, "consumer_constraints") and result.consumer_constraints:
            rprint(f"\n[cyan]Consumer constraints (C):[/cyan]")
            rprint(f"[dim]{result.consumer_constraints}[/dim]")
            human_c = _explain_constraint(result.consumer_constraints)
            if human_c:
                rprint(f"[dim]→ {human_c}[/dim]")

        if hasattr(result, "verification_formula") and result.verification_formula:
            rprint(f"\n[yellow]Verification formula (P ∧ ¬C):[/yellow]")
            rprint(f"[dim]Looking for values that satisfy P but violate C[/dim]")

        rprint("")

    # Show main result
    if result.is_compatible:
        rprint("[green]✓ Schemas are compatible[/green]")
        rprint("Producer schema [blue]⊆[/blue] Consumer schema")

        if show_verification:
            rprint("\n[green]📋 Verification result: UNSAT[/green]")
            rprint("[dim]No counterexample exists - subsumption holds![/dim]")
    else:
        rprint("[red]✗ Schemas are incompatible[/red]")

        if result.error_message:
            rprint(f"[red]Error during verification: {result.error_message}[/red]")
        elif result.counterexample:
            rprint(
                "Found counterexample that satisfies producer but violates consumer:"
            )
            rprint("\n[yellow]Counterexample:[/yellow]")
            rprint(json.dumps(result.counterexample, indent=2))

            # Show enhanced explanations if available
            if hasattr(result, "explanation") and result.explanation:
                rprint("\n[cyan]🧠 Explanation:[/cyan]")
                rprint(f"[dim]{result.explanation}[/dim]")

            if hasattr(result, "failed_constraints") and result.failed_constraints:
                rprint("\n[yellow]⚠️  Failed Constraints:[/yellow]")
                for constraint in result.failed_constraints:
                    rprint(f"[dim]  • {constraint}[/dim]")

            if hasattr(result, "recommendations") and result.recommendations:
                rprint("\n[green]💡 Recommendations:[/green]")
                for rec in result.recommendations:
                    rprint(f"[dim]  • {rec}[/dim]")
        else:
            rprint(
                "Found counterexample that satisfies producer but violates consumer:"
            )
            rprint(
                "[yellow]⚠️  No counterexample was extracted (this might be a bug)[/yellow]"
            )

        if show_verification:
            rprint("\n[red]📋 Verification result: SAT[/red]")
            rprint("[dim]Found a witness that satisfies P but violates C[/dim]")

            if hasattr(result, "z3_model") and result.z3_model:
                rprint(f"\n[yellow]Z3 Model (raw):[/yellow]")
                rprint(f"[dim]{result.z3_model}[/dim]")

    if verbose and result.solver_time:
        rprint(f"\n[dim]Solver time: {result.solver_time:.3f}s[/dim]")


def save_counterexample(counterexample: dict, file_path: Path) -> None:
    """Save counterexample to file."""
    with open(file_path, "w") as f:
        json.dump(counterexample, f, indent=2)


def _format_z3_constraint(constraint_str: str) -> str:
    """Format Z3 constraint string for better readability."""
    if not constraint_str:
        return constraint_str

    # Keep constraints relatively compact but readable
    # Replace some common patterns for readability
    formatted = constraint_str.replace("And(", "And(\n    ")
    formatted = formatted.replace("Or(", "Or(\n    ")
    formatted = formatted.replace("Implies(", "Implies(\n    ")

    # Limit to reasonable length to avoid overwhelming output
    if len(formatted) > 500:
        return constraint_str[:500] + "..."

    return formatted


def _explain_constraint(constraint_str: str) -> str:
    """Provide human-readable explanation of Z3 constraints."""
    if not constraint_str:
        return ""

    # Simple pattern matching for common constraint types
    if "Or(is(str, x), Or(is(int, x), is(real, x)))" in constraint_str:
        return "Accepts strings, integers, or numbers"
    elif "is(str, x)" in constraint_str and constraint_str.count("is(") == 1:
        return "Must be a string"
    elif "is(int, x)" in constraint_str and constraint_str.count("is(") == 1:
        return "Must be an integer"
    elif "is(obj, x)" in constraint_str and "has(x," in constraint_str:
        return "Must be an object with required properties"
    elif "Or(" in constraint_str and "is(" in constraint_str:
        return "Accepts multiple types"
    elif "And(" in constraint_str:
        return "Must satisfy all conditions"

    return ""  # Return empty string if we can't explain it simply


if __name__ == "__main__":
    app()
