"""Validate command: validate JSON data against schemas."""

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from canonizer.core.validator import SchemaValidator, ValidationError, load_schema_from_iglu_uri

app = typer.Typer(help="Validate JSON data against schemas")
console = Console()
console_err = Console(stderr=True)


@app.command()
def run(
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help="Schema URI (Iglu format) or path to JSON Schema file",
    ),
    data: Path = typer.Option(
        None,
        "--data",
        "-d",
        help="Path to JSON data file (or use stdin)",
    ),
    schemas_dir: Path = typer.Option(
        "schemas",
        "--schemas-dir",
        help="Base directory for schema files (for Iglu URIs)",
    ),
):
    """
    Validate JSON data against a schema.

    Examples:
        # Validate using Iglu URI
        can validate run --schema iglu:com.google/gmail/jsonschema/1-0-0 --data input.json

        # Validate using local schema file
        can validate run --schema schemas/test.json --data input.json

        # Validate from stdin
        cat data.json | can validate run --schema schemas/test.json
    """
    try:
        # Read data
        if data:
            data_obj = json.loads(data.read_text())
        else:
            data_text = sys.stdin.read()
            data_obj = json.loads(data_text)

        # Determine schema path
        if schema.startswith("iglu:"):
            # Iglu URI - resolve to local path
            schema_path = load_schema_from_iglu_uri(schema, schemas_dir)
        else:
            # Direct path to schema file
            schema_path = Path(schema)

        # Validate
        validator = SchemaValidator(schema_path)
        validator.validate(data_obj)

        # Success
        console.print("[green]✓[/green] Validation passed", style="bold green")
        console.print(f"Schema: {schema}")
        console.print(f"Data: {data if data else 'stdin'}")

    except FileNotFoundError as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except ValidationError as e:
        console_err.print("[red]✗[/red] Validation failed", style="bold red")
        console_err.print(f"[yellow]Errors ({len(e.errors)}):[/yellow]")
        for error in e.errors:
            console_err.print(f"  - {error}")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        console_err.print(f"[red]JSON Parse Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
