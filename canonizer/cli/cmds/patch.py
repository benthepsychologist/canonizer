"""Patch command: apply schema changes to transforms."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from canonizer.core.differ import SchemaDiff
from canonizer.core.patcher import TransformPatcher, save_patched_transform

app = typer.Typer(help="Apply schema changes to transforms")
console = Console()
console_err = Console(stderr=True)


@app.command()
def transform(
    transform_meta: Path = typer.Option(
        ...,
        "--transform",
        "-t",
        help="Path to transform .meta.yaml file",
        exists=True,
    ),
    patch_file: Path = typer.Option(
        ...,
        "--patch",
        "-p",
        help="Path to patch/diff file (from 'can diff schema')",
        exists=True,
    ),
    output_jsonata: Path = typer.Option(
        None,
        "--output-jsonata",
        "-o",
        help="Output path for updated .jsonata file",
    ),
    output_meta: Path = typer.Option(
        None,
        "--output-meta",
        "-m",
        help="Output path for updated .meta.yaml file",
    ),
    bump_version: bool = typer.Option(
        True,
        "--bump-version/--no-bump-version",
        help="Bump MINOR version (default: true)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Apply even if some changes are skipped",
    ),
):
    """
    Apply schema patch to a transform.

    Limited scope: Only handles ADD (optional fields) and RENAME changes.
    Complex changes require manual review or LLM scaffolding.

    Example:
        can patch transform \\
          --transform transforms/email/gmail.meta.yaml \\
          --patch email_v1_to_v2.patch.json \\
          --output-jsonata transforms/email/gmail_v2.jsonata \\
          --output-meta transforms/email/gmail_v2.meta.yaml
    """
    try:
        # Load patch file (SchemaDiff JSON)
        patch_data = json.loads(patch_file.read_text())
        schema_diff = SchemaDiff(**patch_data)

        # Apply patch
        result = TransformPatcher.patch_transform(
            transform_path=transform_meta,
            schema_diff=schema_diff,
            bump_version=bump_version,
        )

        # Check result
        if not result.success:
            console_err.print(f"[red]✗[/red] Patch failed: {result.error}")
            if result.skipped_changes:
                console_err.print(
                    f"\n[yellow]Skipped {len(result.skipped_changes)} changes:[/yellow]"
                )
                for change in result.skipped_changes:
                    console_err.print(f"  - {change.description}")
            raise typer.Exit(code=1)

        # Success - save results
        if output_jsonata:
            output_jsonata.write_text(result.updated_jsonata)
            console.print(f"[green]✓[/green] Updated JSONata saved to {output_jsonata}")
        else:
            # Print to stdout
            console.print(result.updated_jsonata)

        if output_meta and result.updated_meta:
            save_patched_transform(result, output_jsonata or Path("temp.jsonata"), output_meta)
            console.print(f"[green]✓[/green] Updated meta saved to {output_meta}")

        # Display summary
        summary_table = Table(show_header=False, box=None)
        summary_table.add_column("Key", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Applied changes", str(len(result.applied_changes)))
        summary_table.add_row("Skipped changes", str(len(result.skipped_changes)))
        if bump_version and result.updated_meta:
            summary_table.add_row("Old version", transform_meta.stem.split("_")[-1] if "_" in transform_meta.stem else "N/A")
            summary_table.add_row("New version", result.updated_meta.version)

        console.print(Panel(summary_table, title="Patch Summary", border_style="green"))

        # Show applied changes
        if result.applied_changes:
            console.print("\n[bold]Applied changes:[/bold]")
            for change in result.applied_changes:
                console.print(f"  [green]✓[/green] {change.description}")

        # Show skipped changes
        if result.skipped_changes:
            console.print("\n[bold yellow]Skipped changes (require manual review):[/bold yellow]")
            for change in result.skipped_changes:
                console.print(f"  [yellow]⚠[/yellow] {change.description}")

            if not force:
                console.print(
                    "\n[yellow]Tip:[/yellow] Use [cyan]can scaffold transform[/cyan] with LLM to handle complex changes"
                )

    except FileNotFoundError as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        console_err.print(f"[red]JSON Parse Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
