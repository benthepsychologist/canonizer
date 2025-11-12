"""Diff command: compare two JSON schemas."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from canonizer.core.differ import SchemaDiffer

app = typer.Typer(help="Compare JSON schemas and classify changes")
console = Console()
console_err = Console(stderr=True)


@app.command()
def schema(
    from_schema: Path = typer.Option(
        ...,
        "--from",
        "-f",
        help="Source schema file",
        exists=True,
    ),
    to_schema: Path = typer.Option(
        ...,
        "--to",
        "-t",
        help="Target schema file",
        exists=True,
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output patch file (JSON)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON only (no formatting)",
    ),
):
    """
    Diff two JSON schemas and classify changes.

    Example:
        can diff schema --from schemas/email/v1.json --to schemas/email/v2.json
    """
    try:
        # Perform diff
        diff_result = SchemaDiffer.diff_schemas(from_schema, to_schema)

        # Output results
        if json_output:
            # JSON output
            output_data = diff_result.model_dump(mode="json")
            output_json = json.dumps(output_data, indent=2)

            if output:
                output.write_text(output_json)
                console.print(f"[green]✓[/green] Diff written to {output}")
            else:
                console.print(output_json)

        else:
            # Rich formatted output
            if output:
                # Save as JSON
                output_data = diff_result.model_dump(mode="json")
                output.write_text(json.dumps(output_data, indent=2))
                console.print(f"[green]✓[/green] Diff saved to {output}")

            # Display summary
            console.print("\n[bold]Schema Diff Summary[/bold]")
            console.print(f"From: {from_schema}")
            console.print(f"To:   {to_schema}")
            console.print(
                f"\nTotal changes: [yellow]{len(diff_result.changes)}[/yellow]"
            )
            console.print(
                f"Auto-patchable: [green]{diff_result.auto_patchable_count}[/green]"
            )
            console.print(
                f"Manual review:  [red]{diff_result.manual_review_count}[/red]"
            )

            if diff_result.changes:
                # Display changes table
                console.print("\n[bold]Changes:[/bold]")
                table = Table()
                table.add_column("Type", style="cyan")
                table.add_column("Path", style="white")
                table.add_column("Description", style="dim")
                table.add_column("Auto-patch", justify="center")

                for change in diff_result.changes:
                    auto_patch_icon = (
                        "[green]✓[/green]" if change.auto_patchable else "[red]✗[/red]"
                    )
                    table.add_row(
                        change.change_type.value,
                        change.path,
                        change.description,
                        auto_patch_icon,
                    )

                console.print(table)

                # Show recommendations
                if diff_result.has_auto_patchable:
                    console.print(
                        "\n[green]ℹ[/green] Auto-patchable changes can be applied with [cyan]can patch transform[/cyan]"
                    )
                if diff_result.has_manual_review:
                    console.print(
                        "\n[yellow]⚠[/yellow] Manual review required for some changes"
                    )
            else:
                console.print("\n[dim]No changes detected[/dim]")

    except FileNotFoundError as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        console_err.print(f"[red]JSON Parse Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
