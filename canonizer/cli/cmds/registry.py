"""Registry command: interact with the Canonizer transform registry."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from canonizer.registry.client import RegistryClient

app = typer.Typer(help="Interact with the Canonizer transform registry")
console = Console()
console_err = Console(stderr=True)


@app.command()
def list(
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (draft/stable/deprecated)",
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        "-r",
        help="Force refresh cache (fetch latest index)",
    ),
    registry_url: str | None = typer.Option(
        None,
        "--registry-url",
        help="Custom registry URL (defaults to official registry)",
    ),
):
    """
    List all available transforms from the registry.

    Examples:
        # List all transforms
        can registry list

        # List only stable transforms
        can registry list --status stable

        # Force refresh from registry
        can registry list --refresh
    """
    try:
        client = RegistryClient(registry_url=registry_url)
        transforms = client.list_transforms(use_cache=not refresh)

        if not transforms:
            console.print("[yellow]No transforms found in registry[/yellow]")
            return

        # Filter by status if requested
        if status:
            filtered_transforms = []
            for t in transforms:
                filtered_versions = [v for v in t.get("versions", []) if v.get("status") == status]
                if filtered_versions:
                    filtered_transforms.append({**t, "versions": filtered_versions})
            transforms = filtered_transforms

        if not transforms:
            console.print(f"[yellow]No transforms found with status '{status}'[/yellow]")
            return

        # Display results
        table = Table(title="Available Transforms")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        table.add_column("From Schema", style="blue")
        table.add_column("To Schema", style="magenta")
        table.add_column("Status", style="yellow")

        for transform in transforms:
            transform_id = transform.get("id", "")
            for version_info in transform.get("versions", []):
                table.add_row(
                    transform_id,
                    version_info.get("version", ""),
                    version_info.get("from_schema", ""),
                    version_info.get("to_schema", ""),
                    version_info.get("status", ""),
                )

        console.print(table)
        console.print(f"\n[dim]Total: {sum(len(t.get('versions', [])) for t in transforms)} transform versions[/dim]")

    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def search(
    from_schema: str | None = typer.Option(
        None,
        "--from",
        help="Filter by input schema URI",
    ),
    to_schema: str | None = typer.Option(
        None,
        "--to",
        help="Filter by output schema URI",
    ),
    id: str | None = typer.Option(
        None,
        "--id",
        help="Filter by transform ID",
    ),
    status: str | None = typer.Option(
        None,
        "--status",
        help="Filter by status (draft/stable/deprecated)",
    ),
    registry_url: str | None = typer.Option(
        None,
        "--registry-url",
        help="Custom registry URL (defaults to official registry)",
    ),
):
    """
    Search for transforms by schema URIs, ID, or status.

    Examples:
        # Find transforms from Gmail schema
        can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0

        # Find transforms to canonical email schema
        can registry search --to iglu:org.canonical/email/jsonschema/1-0-0

        # Find specific transform
        can registry search --id email/gmail_to_canonical

        # Combine filters (AND logic)
        can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0 --status stable
    """
    try:
        client = RegistryClient(registry_url=registry_url)
        transforms = client.list_transforms()

        if not transforms:
            console.print("[yellow]No transforms found in registry[/yellow]")
            return

        # Apply filters
        filtered = []
        for transform in transforms:
            transform_id = transform.get("id", "")

            # Filter by ID
            if id and not transform_id.startswith(id):
                continue

            # Filter versions
            filtered_versions = []
            for version_info in transform.get("versions", []):
                # Filter by from_schema
                if from_schema and version_info.get("from_schema") != from_schema:
                    continue

                # Filter by to_schema
                if to_schema and version_info.get("to_schema") != to_schema:
                    continue

                # Filter by status
                if status and version_info.get("status") != status:
                    continue

                filtered_versions.append(version_info)

            if filtered_versions:
                filtered.append({**transform, "versions": filtered_versions})

        if not filtered:
            console.print("[yellow]No transforms match your search criteria[/yellow]")
            return

        # Display results
        table = Table(title="Search Results")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Version", style="green")
        table.add_column("From Schema", style="blue")
        table.add_column("To Schema", style="magenta")
        table.add_column("Status", style="yellow")

        for transform in filtered:
            transform_id = transform.get("id", "")
            for version_info in transform.get("versions", []):
                table.add_row(
                    transform_id,
                    version_info.get("version", ""),
                    version_info.get("from_schema", ""),
                    version_info.get("to_schema", ""),
                    version_info.get("status", ""),
                )

        console.print(table)
        console.print(f"\n[dim]Found: {sum(len(t.get('versions', [])) for t in filtered)} transform versions[/dim]")

    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def pull(
    transform_spec: str = typer.Argument(
        ...,
        help="Transform to pull (format: <id>@<version> or <id>@latest)",
    ),
    registry_url: str | None = typer.Option(
        None,
        "--registry-url",
        help="Custom registry URL (defaults to official registry)",
    ),
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Skip checksum verification (not recommended)",
    ),
):
    """
    Download a transform to local cache.

    Examples:
        # Pull specific version
        can registry pull email/gmail_to_canonical@1.0.0

        # Pull latest version
        can registry pull email/gmail_to_canonical@latest

        # Pull without checksum verification (not recommended)
        can registry pull email/gmail_to_canonical@1.0.0 --no-verify
    """
    try:
        # Parse transform spec
        if "@" not in transform_spec:
            console_err.print("[red]Error:[/red] Transform spec must include version (e.g., id@version or id@latest)")
            raise typer.Exit(code=1)

        transform_id, version = transform_spec.split("@", 1)

        console.print(f"[cyan]Pulling transform:[/cyan] {transform_id}@{version}")

        client = RegistryClient(registry_url=registry_url)
        transform = client.fetch_transform(
            transform_id=transform_id,
            version=version,
            use_cache=False,  # Always fetch fresh on explicit pull
            verify_checksum=not no_verify,
        )

        # Display success
        console.print("[green]✓[/green] Transform downloaded successfully", style="bold green")
        console.print(f"\n[bold]Transform:[/bold] {transform.meta.id}")
        console.print(f"[bold]Version:[/bold] {transform.meta.version}")
        console.print(f"[bold]From:[/bold] {transform.meta.from_schema}")
        console.print(f"[bold]To:[/bold] {transform.meta.to_schema}")
        console.print(f"[bold]Status:[/bold] {transform.meta.status}")
        console.print(f"\n[dim]Cached at:[/dim] {transform.meta_path.parent}")
        console.print(f"[dim]Use with:[/dim] can transform run --meta {transform.meta_path}")

    except ValueError as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def info(
    transform_spec: str = typer.Argument(
        ...,
        help="Transform to get info about (format: <id>@<version> or <id>@latest)",
    ),
    registry_url: str | None = typer.Option(
        None,
        "--registry-url",
        help="Custom registry URL (defaults to official registry)",
    ),
):
    """
    Display detailed information about a transform.

    Examples:
        # Get info about specific version
        can registry info email/gmail_to_canonical@1.0.0

        # Get info about latest version
        can registry info email/gmail_to_canonical@latest
    """
    try:
        # Parse transform spec
        if "@" not in transform_spec:
            console_err.print("[red]Error:[/red] Transform spec must include version (e.g., id@version or id@latest)")
            raise typer.Exit(code=1)

        transform_id, version = transform_spec.split("@", 1)

        client = RegistryClient(registry_url=registry_url)

        # Resolve version first
        resolved_version = client.resolve_version(transform_id, version)
        if not resolved_version:
            console_err.print(f"[red]Error:[/red] Transform not found: {transform_id}@{version}")
            raise typer.Exit(code=1)

        # Get transform info from index
        index = client.fetch_index()
        transforms = index.get("transforms", [])
        transform_entry = next((t for t in transforms if t["id"] == transform_id), None)

        if not transform_entry:
            console_err.print(f"[red]Error:[/red] Transform not found: {transform_id}")
            raise typer.Exit(code=1)

        version_info = next(
            (v for v in transform_entry.get("versions", []) if v["version"] == resolved_version),
            None
        )

        if not version_info:
            console_err.print(f"[red]Error:[/red] Version not found: {resolved_version}")
            raise typer.Exit(code=1)

        # Display info
        console.print("\n[bold cyan]Transform Information[/bold cyan]\n")
        console.print(f"[bold]ID:[/bold] {transform_id}")
        console.print(f"[bold]Version:[/bold] {version_info.get('version')}")
        console.print(f"[bold]Status:[/bold] {version_info.get('status')}")
        console.print("\n[bold]Schema Mapping:[/bold]")
        console.print(f"  [blue]From:[/blue] {version_info.get('from_schema')}")
        console.print(f"  [magenta]To:[/magenta] {version_info.get('to_schema')}")

        if version_info.get("author"):
            console.print(f"\n[bold]Author:[/bold] {version_info.get('author')}")
        if version_info.get("created_utc"):
            console.print(f"[bold]Created:[/bold] {version_info.get('created_utc')}")

        console.print("\n[bold]Checksum:[/bold]")
        console.print(f"  [dim]{version_info.get('checksum', {}).get('jsonata_sha256', 'N/A')}[/dim]")

        console.print(f"\n[bold]Path:[/bold] {version_info.get('path')}")

    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def validate(
    path: Path = typer.Argument(
        ...,
        help="Path to transform directory to validate",
    ),
):
    """
    Validate a transform directory locally (uses same checks as CI).

    Examples:
        # Validate a transform directory
        can registry validate transforms/email/gmail_to_canonical/1.0.0/

        # Validate from registry cache
        can registry validate ~/.cache/canonizer/registry/.../1.0.0/
    """
    console_err.print("[yellow]Note:[/yellow] validate command not yet implemented")
    console_err.print("[dim]This will run the same validation checks as the CI pipeline[/dim]")
    raise typer.Exit(code=1)
