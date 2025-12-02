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
from canonizer.cli.cmds import (  # noqa: E402
    diff,
    import_cmd,  # noqa: E402
    init,
    patch,
    registry,
    transform,
    validate,
)

app.command(name="init")(init.init)
app.add_typer(transform.app, name="transform")
app.add_typer(validate.app, name="validate")
app.add_typer(diff.app, name="diff")
app.add_typer(patch.app, name="patch")
app.add_typer(registry.app, name="registry")
app.add_typer(import_cmd.app, name="import")


if __name__ == "__main__":
    app()
