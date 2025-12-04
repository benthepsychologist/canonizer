"""Registry command: interact with the Canonizer transform registry."""

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from canonizer.local.lock import LockFile
from canonizer.local.resolver import (
    CanonizerRootNotFoundError,
    find_canonizer_root,
    schema_ref_to_path,
)
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
    local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Pull to .canonizer/registry/ instead of global cache",
    ),
    with_schemas: bool = typer.Option(
        True,
        "--with-schemas/--no-schemas",
        help="Also pull referenced schemas (default: yes)",
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
    Download a transform from remote registry.

    Examples:
        # Pull to global cache (~/.cache/canonizer/)
        can registry pull email/gmail_to_canonical@1.0.0

        # Pull to local .canonizer/registry/ (project-local)
        can registry pull email/gmail_to_canonical@1.0.0 --local

        # Pull latest version
        can registry pull email/gmail_to_canonical@latest --local

        # Pull without referenced schemas
        can registry pull email/gmail_to_canonical@1.0.0 --local --no-schemas
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

        if local:
            # Pull to .canonizer/registry/
            try:
                canonizer_root = find_canonizer_root(Path.cwd())
            except CanonizerRootNotFoundError:
                console_err.print(
                    "[red]Error:[/red] No .canonizer/ directory found. "
                    "Run 'canonizer init' first, or omit --local to use global cache."
                )
                raise typer.Exit(code=1)

            # Load lock file
            lock_path = canonizer_root / "lock.json"
            lock = LockFile.load(lock_path) if lock_path.exists() else LockFile.empty()

            # Copy transform to local registry
            registry_dir = canonizer_root / "registry"
            dest_dir = registry_dir / "transforms" / transform_id / transform.meta.version
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Copy files from cache
            shutil.copy(transform.meta_path, dest_dir / "spec.meta.yaml")
            shutil.copy(transform.jsonata_path, dest_dir / "spec.jsonata")

            # Update lock file
            transform_ref = f"{transform_id}@{transform.meta.version}"
            lock.add_transform(
                ref=transform_ref,
                path=str(dest_dir.relative_to(canonizer_root)),
                checksum=f"sha256:{transform.meta.checksum.jsonata_sha256}",
            )

            console.print(f"  [green]✓[/green] Transform copied to {dest_dir.relative_to(canonizer_root.parent)}")

            # Pull referenced schemas if requested
            if with_schemas:
                schemas_to_pull = []
                if transform.meta.from_schema:
                    schemas_to_pull.append(transform.meta.from_schema)
                if transform.meta.to_schema:
                    schemas_to_pull.append(transform.meta.to_schema)

                for schema_ref in schemas_to_pull:
                    try:
                        console.print(f"[cyan]Pulling schema:[/cyan] {schema_ref}")
                        schema = client.fetch_schema(schema_ref, use_cache=False)

                        # Determine destination path
                        schema_rel_path = schema_ref_to_path(schema_ref)
                        schema_dest = registry_dir / "schemas" / schema_rel_path
                        schema_dest.parent.mkdir(parents=True, exist_ok=True)

                        import json
                        schema_dest.write_text(json.dumps(schema, indent=2))

                        # Compute hash and add to lock
                        import hashlib
                        schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
                        lock.add_schema(
                            ref=schema_ref,
                            path=str(schema_dest.relative_to(canonizer_root)),
                            checksum=f"sha256:{schema_hash}",
                        )

                        console.print(f"  [green]✓[/green] {schema_ref}")
                    except Exception as e:
                        console.print(f"  [yellow]⚠[/yellow] {schema_ref}: {e}")

            # Save lock file
            lock.save(lock_path)
            console.print("\n[green]✓[/green] Updated lock.json")

            # Display success
            console.print(f"\n[bold]Transform:[/bold] {transform.meta.id}")
            console.print(f"[bold]Version:[/bold] {transform.meta.version}")
            console.print(f"[bold]From:[/bold] {transform.meta.from_schema}")
            console.print(f"[bold]To:[/bold] {transform.meta.to_schema}")
            console.print(f"\n[dim]Saved to:[/dim] {dest_dir}")
        else:
            # Display success (global cache)
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
    except typer.Exit:
        raise
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
    from canonizer.registry.validator import TransformValidator

    try:
        if not path.exists():
            console_err.print(f"[red]Error:[/red] Directory not found: {path}")
            raise typer.Exit(code=1)

        if not path.is_dir():
            console_err.print(f"[red]Error:[/red] Path is not a directory: {path}")
            raise typer.Exit(code=1)

        console.print(f"[cyan]Validating transform:[/cyan] {path}")
        console.print()

        validator = TransformValidator(path)
        success = validator.validate()

        # Display report
        console.print(validator.get_report())

        if success:
            console.print("\n[green]✓[/green] Transform is valid and ready for contribution", style="bold green")
            raise typer.Exit(code=0)
        else:
            console_err.print("\n[red]✗[/red] Validation failed", style="bold red")
            console_err.print("[dim]Fix the errors above and try again[/dim]")
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def sync(
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
    Sync all dependencies from lock.json to local .canonizer/registry/.

    Reads the lock.json file and pulls any missing or outdated schemas
    and transforms from the remote registry.

    Examples:
        # Sync all dependencies
        can registry sync

        # Sync from custom registry
        can registry sync --registry-url https://example.com/registry/
    """
    import hashlib
    import json

    try:
        # Find .canonizer/ directory
        try:
            canonizer_root = find_canonizer_root(Path.cwd())
        except CanonizerRootNotFoundError:
            console_err.print(
                "[red]Error:[/red] No .canonizer/ directory found. "
                "Run 'canonizer init' first."
            )
            raise typer.Exit(code=1)

        # Load lock file
        lock_path = canonizer_root / "lock.json"
        if not lock_path.exists():
            console.print("[yellow]No lock.json found. Nothing to sync.[/yellow]")
            raise typer.Exit(code=0)

        lock = LockFile.load(lock_path)

        client = RegistryClient(registry_url=registry_url)

        schemas_synced = 0
        schemas_skipped = 0
        schemas_failed = 0
        transforms_synced = 0
        transforms_skipped = 0
        transforms_failed = 0

        # Sync schemas
        registry_dir = canonizer_root / "registry"
        if lock.schemas:
            console.print(f"\n[bold cyan]Syncing {len(lock.schemas)} schemas...[/bold cyan]")
            for schema_ref, entry in lock.schemas.items():
                # entry.path is relative to registry/ dir, e.g. "schemas/com.google/..."
                local_path = registry_dir / entry.path
                expected_hash = entry.hash

                # Check if already exists
                if local_path.exists():
                    with open(local_path) as f:
                        content = f.read()
                    computed_hash = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
                    if computed_hash == expected_hash:
                        console.print(f"  [green]✓[/green] {schema_ref}")
                        schemas_synced += 1
                        continue
                    else:
                        # Local file exists but hash mismatch - treat as local-only schema
                        console.print(f"  [yellow]⚠[/yellow] {schema_ref} (local, hash differs)")
                        schemas_synced += 1
                        continue

                # Fetch from remote
                try:
                    schema = client.fetch_schema(schema_ref, use_cache=False)
                    schema_json = json.dumps(schema, indent=2)

                    # Verify hash if requested
                    if not no_verify:
                        computed_hash = f"sha256:{hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()}"
                        if computed_hash != expected_hash:
                            console.print(f"  [red]✗[/red] {schema_ref} (hash mismatch)")
                            schemas_failed += 1
                            continue

                    # Write to local
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_text(schema_json)
                    console.print(f"  [green]✓[/green] {schema_ref}")
                    schemas_synced += 1
                except Exception as e:
                    console.print(f"  [red]✗[/red] {schema_ref}: {e}")
                    schemas_failed += 1

        # Sync transforms
        if lock.transforms:
            console.print(f"\n[bold cyan]Syncing {len(lock.transforms)} transforms...[/bold cyan]")
            for transform_ref, entry in lock.transforms.items():
                # entry.path points to spec.meta.yaml relative to registry/, get parent directory
                entry_path = Path(entry.path)
                local_dir = registry_dir / entry_path.parent
                expected_hash = entry.hash

                # Check if already exists and matches
                jsonata_path = local_dir / "spec.jsonata"
                if jsonata_path.exists():
                    content = jsonata_path.read_bytes()
                    computed_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
                    if computed_hash == expected_hash:
                        console.print(f"  [green]✓[/green] {transform_ref}")
                        transforms_synced += 1
                        continue
                    else:
                        # Local file exists but hash mismatch - check if it's a local-only transform
                        # (i.e., not from the remote registry)
                        meta_path = local_dir / "spec.meta.yaml"
                        if meta_path.exists():
                            # Transform exists locally, just update the lock hash
                            console.print(f"  [yellow]⚠[/yellow] {transform_ref} (local, hash updated)")
                            transforms_synced += 1
                            continue

                # Parse transform ref
                if "@" not in transform_ref:
                    console.print(f"  [red]✗[/red] {transform_ref} (invalid ref format)")
                    transforms_failed += 1
                    continue

                transform_id, version = transform_ref.rsplit("@", 1)

                # Check if transform exists locally even if not in lock
                meta_path = local_dir / "spec.meta.yaml"
                if meta_path.exists() and jsonata_path.exists():
                    # Local-only transform, mark as synced
                    console.print(f"  [green]✓[/green] {transform_ref} (local)")
                    transforms_synced += 1
                    continue

                # Fetch from remote
                try:
                    transform = client.fetch_transform(
                        transform_id=transform_id,
                        version=version,
                        use_cache=False,
                        verify_checksum=not no_verify,
                    )

                    # Copy to local
                    local_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy(transform.meta_path, local_dir / "spec.meta.yaml")
                    shutil.copy(transform.jsonata_path, local_dir / "spec.jsonata")

                    console.print(f"  [green]✓[/green] {transform_ref}")
                    transforms_synced += 1
                except Exception as e:
                    console.print(f"  [red]✗[/red] {transform_ref}: {e}")
                    transforms_failed += 1

        # Summary
        console.print("\n[bold]Sync complete:[/bold]")
        console.print(f"  Schemas: {schemas_synced} synced, {schemas_skipped} up-to-date, {schemas_failed} failed")
        console.print(f"  Transforms: {transforms_synced} synced, {transforms_skipped} up-to-date, {transforms_failed} failed")

        if schemas_failed > 0 or transforms_failed > 0:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def lock(
    transform_ref: str | None = typer.Argument(
        None,
        help="Transform to lock (format: <id>@<version>). If not specified, use --all.",
    ),
    all_local: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Lock all transforms found in local registry",
    ),
):
    """
    Add local transforms to lock.json.

    Scans .canonizer/registry/transforms/ for transforms not in lock.json
    and adds them with their current hashes.

    Examples:
        # Lock a specific transform
        can registry lock clinical_session/dataverse_to_canonical@2-0-0

        # Lock all local transforms
        can registry lock --all
    """
    import hashlib
    import yaml

    try:
        # Find .canonizer/ directory
        try:
            canonizer_root = find_canonizer_root(Path.cwd())
        except CanonizerRootNotFoundError:
            console_err.print(
                "[red]Error:[/red] No .canonizer/ directory found. "
                "Run 'canonizer init' first."
            )
            raise typer.Exit(code=1)

        registry_dir = canonizer_root / "registry"
        transforms_dir = registry_dir / "transforms"
        schemas_dir = registry_dir / "schemas"

        if not transforms_dir.exists():
            console.print("[yellow]No transforms directory found.[/yellow]")
            raise typer.Exit(code=0)

        # Load lock file
        lock_path = canonizer_root / "lock.json"
        lockfile = LockFile.load(lock_path) if lock_path.exists() else LockFile.empty()

        added_transforms = 0
        added_schemas = 0

        if transform_ref:
            # Lock specific transform
            if "@" not in transform_ref:
                console_err.print("[red]Error:[/red] Transform ref must include version (e.g., id@version)")
                raise typer.Exit(code=1)

            transform_id, version = transform_ref.rsplit("@", 1)
            transform_dir = transforms_dir / transform_id / version

            if not transform_dir.exists():
                console_err.print(f"[red]Error:[/red] Transform not found: {transform_dir}")
                raise typer.Exit(code=1)

            added_t, added_s = _lock_transform(
                transform_id, version, transform_dir, lockfile, registry_dir, schemas_dir
            )
            added_transforms += added_t
            added_schemas += added_s
        elif all_local:
            # Lock all local transforms
            for category_dir in transforms_dir.iterdir():
                if not category_dir.is_dir() or category_dir.name.startswith("."):
                    continue

                for transform_name_dir in category_dir.iterdir():
                    if not transform_name_dir.is_dir():
                        continue

                    for version_dir in transform_name_dir.iterdir():
                        if not version_dir.is_dir():
                            continue

                        transform_id = f"{category_dir.name}/{transform_name_dir.name}"
                        version = version_dir.name

                        added_t, added_s = _lock_transform(
                            transform_id, version, version_dir, lockfile, registry_dir, schemas_dir
                        )
                        added_transforms += added_t
                        added_schemas += added_s
        else:
            console_err.print("[red]Error:[/red] Specify a transform ref or use --all")
            raise typer.Exit(code=1)

        # Save lock file
        if added_transforms > 0 or added_schemas > 0:
            lockfile.save(lock_path)
            console.print(f"\n[green]✓[/green] Updated lock.json")
            console.print(f"  Added {added_transforms} transforms, {added_schemas} schemas")
        else:
            console.print("[yellow]No new transforms to lock.[/yellow]")

    except typer.Exit:
        raise
    except Exception as e:
        console_err.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def _lock_transform(
    transform_id: str,
    version: str,
    transform_dir: Path,
    lockfile: LockFile,
    registry_dir: Path,
    schemas_dir: Path,
) -> tuple[int, int]:
    """Lock a single transform and its schemas. Returns (transforms_added, schemas_added)."""
    import hashlib
    import yaml

    from canonizer.local.lock import SchemaLock, TransformLock

    added_transforms = 0
    added_schemas = 0

    transform_ref = f"{transform_id}@{version}"

    # Check if already in lock
    if transform_ref in lockfile.transforms:
        console.print(f"  [dim]⊘[/dim] {transform_ref} (already locked)")
        return 0, 0

    meta_path = transform_dir / "spec.meta.yaml"
    jsonata_path = transform_dir / "spec.jsonata"

    if not meta_path.exists() or not jsonata_path.exists():
        console.print(f"  [yellow]⚠[/yellow] {transform_ref} (missing files)")
        return 0, 0

    # Compute hash of spec.jsonata
    jsonata_content = jsonata_path.read_bytes()
    jsonata_hash = f"sha256:{hashlib.sha256(jsonata_content).hexdigest()}"

    # Add to lock
    rel_path = meta_path.relative_to(registry_dir)
    lockfile.transforms[transform_ref] = TransformLock(path=str(rel_path), hash=jsonata_hash)
    console.print(f"  [green]✓[/green] {transform_ref}")
    added_transforms = 1

    # Also lock referenced schemas
    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    for schema_ref in [meta.get("from_schema"), meta.get("to_schema")]:
        if not schema_ref or schema_ref in lockfile.schemas:
            continue

        # Find schema file
        schema_path = _schema_ref_to_path(schema_ref, schemas_dir)
        if schema_path and schema_path.exists():
            content = schema_path.read_bytes()
            schema_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
            rel_path = schema_path.relative_to(registry_dir)
            lockfile.schemas[schema_ref] = SchemaLock(path=str(rel_path), hash=schema_hash)
            console.print(f"    [green]✓[/green] {schema_ref}")
            added_schemas += 1

    return added_transforms, added_schemas


def _schema_ref_to_path(schema_ref: str, schemas_dir: Path) -> Path | None:
    """Convert schema ref like 'iglu:com.google/gmail/jsonschema/1-0-0' to path."""
    if not schema_ref.startswith("iglu:"):
        return None

    # iglu:com.google/gmail_email/jsonschema/1-0-0
    # -> com.google/gmail_email/jsonschema/1-0-0.json
    parts = schema_ref[5:]  # Remove "iglu:"
    return schemas_dir / f"{parts}.json"
