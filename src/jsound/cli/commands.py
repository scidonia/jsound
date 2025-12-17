"""CLI commands for jsound."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

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
        )

        # Perform subsumption check
        checker = SubsumptionChecker(config)

        if verbose:
            console.print("[blue]Starting subsumption check...[/blue]")

        result = checker.check_subsumption(producer_schema, consumer_schema)

        # Handle output
        if output_format == "json":
            output_json(result)
        elif output_format == "minimal":
            output_minimal(result)
        else:  # pretty
            output_pretty(result, verbose)

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


def output_json(result: CheckResult) -> None:
    """Output result in JSON format."""
    output = {
        "compatible": result.is_compatible,
        "counterexample": result.counterexample,
        "solver_time": result.solver_time,
    }
    if result.error_message:
        output["error"] = result.error_message
    print(json.dumps(output, indent=2))


def output_minimal(result: CheckResult) -> None:
    """Output result in minimal format."""
    if result.is_compatible:
        print("compatible")
    else:
        print("incompatible")
        if result.counterexample:
            print(json.dumps(result.counterexample))


def output_pretty(result: CheckResult, verbose: bool = False) -> None:
    """Output result in pretty format."""
    if result.is_compatible:
        rprint("[green]✓ Schemas are compatible[/green]")
        rprint("Producer schema [blue]⊆[/blue] Consumer schema")
    else:
        rprint("[red]✗ Schemas are incompatible[/red]")
        rprint("Found counterexample that satisfies producer but violates consumer:")

        if result.counterexample:
            rprint("\n[yellow]Counterexample:[/yellow]")
            rprint(json.dumps(result.counterexample, indent=2))

    if verbose and result.solver_time:
        rprint(f"\n[dim]Solver time: {result.solver_time:.3f}s[/dim]")


def save_counterexample(counterexample: dict, file_path: Path) -> None:
    """Save counterexample to file."""
    with open(file_path, "w") as f:
        json.dump(counterexample, f, indent=2)


if __name__ == "__main__":
    app()
