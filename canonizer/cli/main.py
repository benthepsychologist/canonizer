"""Main CLI application for Canonizer."""

import typer
from rich.console import Console

app = typer.Typer(
    name="can",
    help="Canonizer: Pure JSON transformation tool. No ingestion. No storage. Just transforms.",
    add_completion=False,
)

console = Console()


@app.command()
def version():
    """Show Canonizer version."""
    from canonizer import __version__

    console.print(f"Canonizer version {__version__}", style="bold green")


# Import commands
from canonizer.cli.cmds import diff, patch, transform, validate  # noqa: E402

app.add_typer(transform.app, name="transform")
app.add_typer(validate.app, name="validate")
app.add_typer(diff.app, name="diff")
app.add_typer(patch.app, name="patch")


if __name__ == "__main__":
    app()
