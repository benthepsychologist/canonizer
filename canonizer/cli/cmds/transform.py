"""Transform command: execute JSON transformations."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from canonizer.core.runtime import TransformRuntime
from canonizer.core.validator import ValidationError

app = typer.Typer(help="Execute JSON transformations")
console = Console()
console_err = Console(stderr=True)


@app.command()
def run(
    meta: Path = typer.Option(
        ...,
        "--meta",
        "-m",
        help="Path to transform .meta.yaml file",
        exists=True,
    ),
    input: Path = typer.Option(
        None,
        "--input",
        "-i",
        help="Path to input JSON file (or use stdin)",
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to output JSON file (or use stdout)",
    ),
    schemas_dir: Path = typer.Option(
        "schemas",
        "--schemas-dir",
        "-s",
        help="Base directory for schema files",
    ),
    validate_input: bool = typer.Option(
        True,
        "--validate-input/--no-validate-input",
        help="Validate input against from_schema",
    ),
    validate_output: bool = typer.Option(
        True,
        "--validate-output/--no-validate-output",
        help="Validate output against to_schema",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON only (no formatting)",
    ),
):
    """
    Execute a transform on input data.

    Example:
        can transform run --meta transforms/gmail.meta.yaml --input data.json
    """
    try:
        # Read input
        if input:
            input_data = json.loads(input.read_text())
        else:
            input_text = sys.stdin.read()
            input_data = json.loads(input_text)

        # Execute transform
        runtime = TransformRuntime(schemas_dir=schemas_dir)
        result = runtime.execute(
            transform_meta_path=meta,
            input_data=input_data,
            validate_input=validate_input,
            validate_output=validate_output,
        )

        # Output result
        if json_output:
            # JSON-only output
            output_data = {
                "data": result.data,
                "execution_time_ms": result.execution_time_ms,
                "runtime": result.runtime,
            }

            output_json = json.dumps(output_data, indent=2)

            if output:
                output.write_text(output_json)
            else:
                console.print(output_json)
        else:
            # Rich formatted output
            if output:
                output.write_text(json.dumps(result.data, indent=2))
                console.print(f"[green]✓[/green] Output written to {output}")
            else:
                console.print(json.dumps(result.data, indent=2))

            # Show execution info
            info_table = Table(show_header=False, box=None)
            info_table.add_column("Key", style="cyan")
            info_table.add_column("Value", style="white")
            info_table.add_row("Runtime", result.runtime)
            info_table.add_row(
                "Execution Time", f"{result.execution_time_ms:.2f}ms"
            )
            info_table.add_row("Status", "[green]success[/green]")

            console.print(
                Panel(info_table, title="Transform Execution", border_style="green")
            )

    except FileNotFoundError as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except ValidationError as e:
        console_err.print(f"[red]Validation Error:[/red] {e}")
        console_err.print("[yellow]Errors:[/yellow]")
        for error in e.errors:
            console_err.print(f"  - {error}")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        console_err.print(f"[red]JSON Parse Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def list(
    transforms_dir: Path = typer.Option(
        "transforms",
        "--dir",
        "-d",
        help="Directory to search for transforms",
    ),
):
    """
    List all available transforms.

    Example:
        can transform list --dir transforms/
    """
    from canonizer.registry.loader import TransformLoader

    try:
        meta_files = TransformLoader.discover(transforms_dir)

        if not meta_files:
            console.print(f"[yellow]No transforms found in {transforms_dir}[/yellow]")
            return

        table = Table(title=f"Transforms in {transforms_dir}")
        table.add_column("ID", style="cyan")
        table.add_column("Version", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("From → To", style="white")

        for meta_file in meta_files:
            transform = TransformLoader.load(meta_file)
            table.add_row(
                transform.meta.id,
                transform.meta.version,
                transform.meta.status,
                f"{transform.meta.from_schema.split('/')[-2]} → {transform.meta.to_schema.split('/')[-2]}",
            )

        console.print(table)

    except FileNotFoundError:
        console_err.print(f"[red]Directory not found:[/red] {transforms_dir}")
        raise typer.Exit(code=1)
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
