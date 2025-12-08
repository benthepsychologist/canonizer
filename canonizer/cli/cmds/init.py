"""CLI command for initializing a local .canonizer/ directory."""

from pathlib import Path

import typer
from rich.console import Console

from canonizer.local.config import (
    CANONIZER_DIR,
    CONFIG_FILENAME,
    LOCK_FILENAME,
    REGISTRY_DIR,
    SCHEMAS_DIR,
    TRANSFORMS_DIR,
    CanonizerConfig,
)
from canonizer.local.lock import LockFile
from canonizer.config import get_canonizer_home

console = Console()


def init(
    path: Path | None = typer.Argument(
        None,
        help="Directory to initialize (defaults to current directory)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing .canonizer/ directory",
    ),
    is_global: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Initialize in global config directory (~/.config/canonizer)",
    ),
) -> None:
    """Initialize a .canonizer/ directory for schema and transform resolution.

    Creates the following structure:

        .canonizer/ (or ~/.config/canonizer/)
        ├── config.yaml       # Registry configuration
        ├── lock.json         # Pinned refs + hashes
        └── registry/         # Local copies of schemas and transforms
            ├── schemas/
            └── transforms/

    Example usage:
        canonizer init
        canonizer init --global
        canonizer init ./my-project
        canonizer init --force
    """
    # Determine target directory
    if is_global:
        if path:
            console.print("[red]Error:[/red] Cannot specify path with --global")
            raise typer.Exit(code=1)
        # For global, we initialize directly into the home dir, NOT inside a .canonizer subdir
        # Wait, existing logic expects .canonizer/config.yaml.
        # But global usually is ~/.config/canonizer/config.yaml.
        # Let's see how resolver looks for it:
        # if (global_home / CONFIG_FILENAME).exists():
        # global_home is get_canonizer_home() -> ~/.config/canonizer
        # So we should write to ~/.config/canonizer directly, not ~/.config/canonizer/.canonizer
        canonizer_dir = get_canonizer_home()
        # Ensure parent exists
        canonizer_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = (path or Path.cwd()).resolve()
        if not target_dir.exists():
            console.print(f"[red]Error:[/red] Directory does not exist: {target_dir}")
            raise typer.Exit(code=1)
        canonizer_dir = target_dir / CANONIZER_DIR

    # Check for existing directory
    if canonizer_dir.exists() and not force:
        # If global and dir exists, check if config exists
        if is_global:
             if (canonizer_dir / CONFIG_FILENAME).exists():
                console.print(
                    f"[yellow]Warning:[/yellow] {canonizer_dir} already initialized. "
                    "Use --force to overwrite."
                )
                raise typer.Exit(code=1)
        else:
            console.print(
                f"[yellow]Warning:[/yellow] {canonizer_dir} already exists. "
                "Use --force to overwrite."
            )
            raise typer.Exit(code=1)

    try:
        # Create directory structure
        console.print(f"[blue]Initializing[/blue] {canonizer_dir}")

        # Create directories
        registry_dir = canonizer_dir / REGISTRY_DIR
        schemas_dir = registry_dir / SCHEMAS_DIR
        transforms_dir = registry_dir / TRANSFORMS_DIR

        schemas_dir.mkdir(parents=True, exist_ok=True)
        transforms_dir.mkdir(parents=True, exist_ok=True)

        # Create config.yaml
        config_path = canonizer_dir / CONFIG_FILENAME
        config = CanonizerConfig.default()
        config.save(config_path)
        console.print(f"  [green]✓[/green] Created {CONFIG_FILENAME}")

        # Create lock.json
        lock_path = canonizer_dir / LOCK_FILENAME
        lock = LockFile.empty()
        lock.save(lock_path)
        console.print(f"  [green]✓[/green] Created {LOCK_FILENAME}")

        # Create .gitignore for registry (don't commit downloaded files)
        gitignore_path = canonizer_dir / ".gitignore"
        gitignore_content = """# Downloaded registry files (fetch via canonizer import)
registry/

# Cache files
*.pyc
__pycache__/
"""
        gitignore_path.write_text(gitignore_content)
        console.print("  [green]✓[/green] Created .gitignore")

        # Summary
        console.print()
        if is_global:
            console.print("[green]✓ Initialized[/green] global canonizer registry")
        else:
            console.print("[green]✓ Initialized[/green] local canonizer registry")
        console.print()
        console.print("[dim]Next steps:[/dim]")
        console.print("  1. Import schemas/transforms from a registry repo:")
        console.print(
            "     [cyan]canonizer import --from /path/to/canonizer-registry "
            "--ref iglu:com.google/gmail_email/jsonschema/1-0-0[/cyan]"
        )
        console.print("  2. Or copy files manually to .canonizer/registry/")
        console.print("  3. Commit config.yaml and lock.json to version control")

    except OSError as e:
        console.print(f"[red]Error:[/red] Failed to initialize: {e}")
        raise typer.Exit(code=1)


# Create the typer app for this command
# Note: This is a standalone command, not a subcommand group
app = typer.Typer(
    name="init",
    help="Initialize local .canonizer/ directory",
    invoke_without_command=True,
    callback=init,
)
