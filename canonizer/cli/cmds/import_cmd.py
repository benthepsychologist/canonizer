"""CLI command for importing schemas and transforms from a registry repo."""

import shutil
from pathlib import Path

import typer
from rich.console import Console

from canonizer.local.config import (
    CONFIG_FILENAME,
    CanonizerConfig,
)
from canonizer.local.lock import LockFile
from canonizer.local.resolver import (
    CanonizerRootNotFoundError,
    InvalidReferenceError,
    find_canonizer_root,
    parse_transform_ref,
    schema_ref_to_path,
    transform_ref_to_path,
)

app = typer.Typer(
    name="import",
    help="Import schemas and transforms from a registry repository",
)

console = Console()


def detect_ref_type(ref: str) -> str:
    """Detect whether a reference is a schema or transform.

    Args:
        ref: Reference string

    Returns:
        "schema" or "transform"

    Raises:
        InvalidReferenceError: If reference format is not recognized
    """
    if ref.startswith("iglu:"):
        return "schema"
    elif "@" in ref:
        return "transform"
    else:
        raise InvalidReferenceError(
            f"Cannot determine reference type: {ref}\n"
            f"Schema refs start with 'iglu:', transform refs contain '@'"
        )


def import_schema(
    ref: str,
    source_registry: Path,
    canonizer_root: Path,
    config: CanonizerConfig,
    lock: LockFile,
) -> Path:
    """Import a schema from source registry to local .canonizer/.

    Args:
        ref: Schema reference (iglu:vendor/name/jsonschema/version)
        source_registry: Path to source registry repo
        canonizer_root: Path to .canonizer/ directory
        config: Canonizer configuration
        lock: Lock file to update

    Returns:
        Path to imported schema file

    Raises:
        FileNotFoundError: If schema not found in source registry
    """
    # Parse reference to get relative path
    rel_path = schema_ref_to_path(ref)

    # Source path in registry repo
    source_path = source_registry / rel_path
    if not source_path.exists():
        raise FileNotFoundError(
            f"Schema not found in source registry: {ref}\n"
            f"Expected at: {source_path}"
        )

    # Destination path in .canonizer/
    registry_path = config.get_registry_path(canonizer_root)
    dest_path = registry_path / rel_path

    # Create parent directories
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(source_path, dest_path)

    # Update lock file
    content = dest_path.read_bytes()
    lock.add_schema(ref, rel_path, content)

    return dest_path


def import_transform(
    ref: str,
    source_registry: Path,
    canonizer_root: Path,
    config: CanonizerConfig,
    lock: LockFile,
) -> Path:
    """Import a transform from source registry to local .canonizer/.

    Args:
        ref: Transform reference (category/name@version)
        source_registry: Path to source registry repo
        canonizer_root: Path to .canonizer/ directory
        config: Canonizer configuration
        lock: Lock file to update

    Returns:
        Path to imported transform directory

    Raises:
        FileNotFoundError: If transform not found in source registry
    """
    # Parse reference
    transform_id, version = parse_transform_ref(ref)

    # Source directory in registry repo
    source_dir = source_registry / "transforms" / transform_id / version
    if not source_dir.exists():
        raise FileNotFoundError(
            f"Transform not found in source registry: {ref}\n"
            f"Expected at: {source_dir}"
        )

    # Destination directory in .canonizer/
    registry_path = config.get_registry_path(canonizer_root)
    dest_dir = registry_path / "transforms" / transform_id / version

    # Create parent directories and copy entire transform directory
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(source_dir, dest_dir)

    # Update lock file with jsonata hash
    jsonata_path = dest_dir / "spec.jsonata"
    if jsonata_path.exists():
        jsonata_content = jsonata_path.read_bytes()
        rel_path = transform_ref_to_path(ref)
        lock.add_transform(ref, rel_path, jsonata_content)

    return dest_dir


@app.command("run")
def import_run(
    ref: str = typer.Argument(
        ...,
        help="Reference to import (schema: iglu:vendor/name/jsonschema/version, transform: category/name@version)",
    ),
    source: Path = typer.Option(
        ...,
        "--from",
        "-f",
        help="Path to source registry repository",
    ),
    target: Path | None = typer.Option(
        None,
        "--to",
        "-t",
        help="Path to project with .canonizer/ (defaults to current directory)",
    ),
    with_schemas: bool = typer.Option(
        True,
        "--with-schemas/--no-schemas",
        help="Also import referenced schemas when importing a transform",
    ),
) -> None:
    """Import a schema or transform from a registry repository.

    Examples:
        # Import a schema
        canonizer import run --from ../canonizer-registry \\
            iglu:com.google/gmail_email/jsonschema/1-0-0

        # Import a transform (also imports its schemas by default)
        canonizer import run --from ../canonizer-registry \\
            email/gmail_to_jmap_lite@1.0.0

        # Import transform without schemas
        canonizer import run --from ../canonizer-registry \\
            --no-schemas email/gmail_to_jmap_lite@1.0.0
    """
    # Validate source registry
    source = source.resolve()
    if not source.exists():
        console.print(f"[red]Error:[/red] Source registry not found: {source}")
        raise typer.Exit(code=1)

    # Check it looks like a registry
    if not (source / "schemas").exists() and not (source / "transforms").exists():
        console.print(
            f"[yellow]Warning:[/yellow] {source} doesn't look like a registry "
            "(no schemas/ or transforms/ directory)"
        )

    # Find .canonizer/ directory
    try:
        start_path = target or Path.cwd()
        canonizer_root = find_canonizer_root(start_path)
    except CanonizerRootNotFoundError:
        console.print(
            "[red]Error:[/red] No .canonizer/ directory found. "
            "Run 'canonizer init' first."
        )
        raise typer.Exit(code=1)

    # Load config and lock
    config = CanonizerConfig.load(canonizer_root / CONFIG_FILENAME)
    lock_path = canonizer_root / "lock.json"
    lock = LockFile.load(lock_path) if lock_path.exists() else LockFile.empty()

    try:
        ref_type = detect_ref_type(ref)

        if ref_type == "schema":
            console.print(f"[blue]Importing schema:[/blue] {ref}")
            dest = import_schema(ref, source, canonizer_root, config, lock)
            console.print(f"  [green]✓[/green] Copied to {dest.relative_to(canonizer_root.parent)}")

        elif ref_type == "transform":
            console.print(f"[blue]Importing transform:[/blue] {ref}")
            dest = import_transform(ref, source, canonizer_root, config, lock)
            console.print(f"  [green]✓[/green] Copied to {dest.relative_to(canonizer_root.parent)}")

            # Import referenced schemas if requested
            if with_schemas:
                meta_path = dest / "spec.meta.yaml"
                if meta_path.exists():
                    import yaml
                    with open(meta_path) as f:
                        meta = yaml.safe_load(f)

                    schemas_to_import = []
                    if "from_schema" in meta:
                        schemas_to_import.append(meta["from_schema"])
                    if "to_schema" in meta:
                        schemas_to_import.append(meta["to_schema"])

                    for schema_ref in schemas_to_import:
                        try:
                            console.print(f"[blue]Importing schema:[/blue] {schema_ref}")
                            schema_dest = import_schema(schema_ref, source, canonizer_root, config, lock)
                            console.print(f"  [green]✓[/green] Copied to {schema_dest.relative_to(canonizer_root.parent)}")
                        except FileNotFoundError:
                            console.print(f"  [yellow]⚠[/yellow] Schema not found: {schema_ref}")

        # Save updated lock file
        lock.save(lock_path)
        console.print("\n[green]✓[/green] Updated lock.json")

    except InvalidReferenceError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def collect_schema_refs(source_registry: Path) -> list[str]:
    """Collect all schema references from a registry directory.

    Args:
        source_registry: Path to source registry repo

    Returns:
        List of schema references (iglu:vendor/name/jsonschema/version)
    """
    refs = []
    schemas_dir = source_registry / "schemas"
    if schemas_dir.exists():
        for vendor_dir in sorted(schemas_dir.iterdir()):
            if vendor_dir.is_dir():
                for schema_dir in sorted(vendor_dir.iterdir()):
                    if schema_dir.is_dir():
                        jsonschema_dir = schema_dir / "jsonschema"
                        if jsonschema_dir.exists():
                            for version_file in sorted(jsonschema_dir.glob("*.json")):
                                version = version_file.stem
                                ref = f"iglu:{vendor_dir.name}/{schema_dir.name}/jsonschema/{version}"
                                refs.append(ref)
    return refs


def collect_transform_refs(
    source_registry: Path, category: str | None = None
) -> list[str]:
    """Collect all transform references from a registry directory.

    Args:
        source_registry: Path to source registry repo
        category: Optional category filter (e.g., 'email', 'forms')

    Returns:
        List of transform references (category/name@version)
    """
    refs = []
    transforms_dir = source_registry / "transforms"
    if transforms_dir.exists():
        for cat_dir in sorted(transforms_dir.iterdir()):
            if cat_dir.is_dir():
                if category and cat_dir.name != category:
                    continue
                for transform_dir in sorted(cat_dir.iterdir()):
                    if transform_dir.is_dir():
                        for version_dir in sorted(transform_dir.iterdir()):
                            if version_dir.is_dir() and (version_dir / "spec.meta.yaml").exists():
                                ref = f"{cat_dir.name}/{transform_dir.name}@{version_dir.name}"
                                refs.append(ref)
    return refs


@app.command("all")
def import_all(
    source: Path = typer.Option(
        ...,
        "--from",
        "-f",
        help="Path to source registry repository",
    ),
    target: Path | None = typer.Option(
        None,
        "--to",
        "-t",
        help="Path to project with .canonizer/ (defaults to current directory)",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter transforms by category (e.g., 'email', 'forms')",
    ),
    schemas_only: bool = typer.Option(
        False,
        "--schemas-only",
        help="Import only schemas (no transforms)",
    ),
    transforms_only: bool = typer.Option(
        False,
        "--transforms-only",
        help="Import only transforms (and their referenced schemas)",
    ),
) -> None:
    """Bulk import all schemas and transforms from a registry repository.

    Examples:
        # Import everything
        canonizer import all --from ../canonizer-registry

        # Import only email transforms
        canonizer import all --from ../canonizer-registry --category email

        # Import only schemas
        canonizer import all --from ../canonizer-registry --schemas-only

        # Import only transforms (with their referenced schemas)
        canonizer import all --from ../canonizer-registry --transforms-only
    """
    # Validate source registry
    source = source.resolve()
    if not source.exists():
        console.print(f"[red]Error:[/red] Source registry not found: {source}")
        raise typer.Exit(code=1)

    # Check it looks like a registry
    if not (source / "schemas").exists() and not (source / "transforms").exists():
        console.print(
            f"[yellow]Warning:[/yellow] {source} doesn't look like a registry "
            "(no schemas/ or transforms/ directory)"
        )

    # Validate mutually exclusive options
    if schemas_only and transforms_only:
        console.print(
            "[red]Error:[/red] Cannot use --schemas-only and --transforms-only together"
        )
        raise typer.Exit(code=1)

    # Find .canonizer/ directory
    try:
        start_path = target or Path.cwd()
        canonizer_root = find_canonizer_root(start_path)
    except CanonizerRootNotFoundError:
        console.print(
            "[red]Error:[/red] No .canonizer/ directory found. "
            "Run 'canonizer init' first."
        )
        raise typer.Exit(code=1)

    # Load config and lock
    config = CanonizerConfig.load(canonizer_root / CONFIG_FILENAME)
    lock_path = canonizer_root / "lock.json"
    lock = LockFile.load(lock_path) if lock_path.exists() else LockFile.empty()

    # Collect refs to import
    schema_refs: list[str] = []
    transform_refs: list[str] = []

    if not transforms_only:
        schema_refs = collect_schema_refs(source)

    if not schemas_only:
        transform_refs = collect_transform_refs(source, category)

    # Show summary
    console.print(f"\n[bold]Source registry:[/bold] {source}")
    console.print(f"[bold]Target:[/bold] {canonizer_root}")
    if category:
        console.print(f"[bold]Category filter:[/bold] {category}")
    console.print(f"\n[bold]Found:[/bold] {len(schema_refs)} schemas, {len(transform_refs)} transforms")

    if not schema_refs and not transform_refs:
        console.print("[yellow]Nothing to import.[/yellow]")
        raise typer.Exit(code=0)

    # Import schemas
    schemas_imported = 0
    schemas_failed = 0

    if schema_refs:
        console.print(f"\n[bold cyan]Importing {len(schema_refs)} schemas...[/bold cyan]")
        for ref in schema_refs:
            try:
                dest = import_schema(ref, source, canonizer_root, config, lock)
                console.print(f"  [green]✓[/green] {ref}")
                schemas_imported += 1
            except FileNotFoundError as e:
                console.print(f"  [red]✗[/red] {ref}: {e}")
                schemas_failed += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] {ref}: {e}")
                schemas_failed += 1

    # Import transforms
    transforms_imported = 0
    transforms_failed = 0
    schemas_from_transforms = 0

    if transform_refs:
        console.print(f"\n[bold cyan]Importing {len(transform_refs)} transforms...[/bold cyan]")
        for ref in transform_refs:
            try:
                dest = import_transform(ref, source, canonizer_root, config, lock)
                console.print(f"  [green]✓[/green] {ref}")
                transforms_imported += 1

                # Import referenced schemas if transforms_only mode
                # (In regular mode, schemas are already imported above)
                if transforms_only:
                    meta_path = dest / "spec.meta.yaml"
                    if meta_path.exists():
                        import yaml
                        with open(meta_path) as f:
                            meta = yaml.safe_load(f)

                        for schema_key in ["from_schema", "to_schema"]:
                            if schema_key in meta:
                                schema_ref = meta[schema_key]
                                try:
                                    import_schema(schema_ref, source, canonizer_root, config, lock)
                                    console.print(f"    [green]✓[/green] {schema_ref}")
                                    schemas_from_transforms += 1
                                except FileNotFoundError:
                                    console.print(f"    [yellow]⚠[/yellow] {schema_ref} (not found)")
                                except Exception as e:
                                    console.print(f"    [yellow]⚠[/yellow] {schema_ref}: {e}")

            except FileNotFoundError as e:
                console.print(f"  [red]✗[/red] {ref}: {e}")
                transforms_failed += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] {ref}: {e}")
                transforms_failed += 1

    # Save lock file
    lock.save(lock_path)

    # Summary
    console.print("\n[bold]Import complete:[/bold]")
    console.print(f"  Schemas: {schemas_imported} imported, {schemas_failed} failed")
    if transforms_only and schemas_from_transforms > 0:
        console.print(f"  Schemas (from transforms): {schemas_from_transforms} imported")
    console.print(f"  Transforms: {transforms_imported} imported, {transforms_failed} failed")
    console.print("\n[green]✓[/green] Updated lock.json")

    if schemas_failed > 0 or transforms_failed > 0:
        raise typer.Exit(code=1)


@app.command("list")
def import_list(
    source: Path = typer.Option(
        ...,
        "--from",
        "-f",
        help="Path to source registry repository",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category (e.g., 'email', 'forms')",
    ),
) -> None:
    """List available schemas and transforms in a registry repository.

    Example:
        canonizer import list --from ../canonizer-registry
        canonizer import list --from ../canonizer-registry --category email
    """
    source = source.resolve()
    if not source.exists():
        console.print(f"[red]Error:[/red] Source registry not found: {source}")
        raise typer.Exit(code=1)

    # List schemas
    schemas_dir = source / "schemas"
    if schemas_dir.exists():
        console.print("\n[bold]Schemas:[/bold]")
        for vendor_dir in sorted(schemas_dir.iterdir()):
            if vendor_dir.is_dir():
                for schema_dir in sorted(vendor_dir.iterdir()):
                    if schema_dir.is_dir():
                        jsonschema_dir = schema_dir / "jsonschema"
                        if jsonschema_dir.exists():
                            for version_file in sorted(jsonschema_dir.glob("*.json")):
                                version = version_file.stem
                                ref = f"iglu:{vendor_dir.name}/{schema_dir.name}/jsonschema/{version}"
                                console.print(f"  {ref}")

    # List transforms
    transforms_dir = source / "transforms"
    if transforms_dir.exists():
        console.print("\n[bold]Transforms:[/bold]")
        for cat_dir in sorted(transforms_dir.iterdir()):
            if cat_dir.is_dir():
                if category and cat_dir.name != category:
                    continue
                for transform_dir in sorted(cat_dir.iterdir()):
                    if transform_dir.is_dir():
                        for version_dir in sorted(transform_dir.iterdir()):
                            if version_dir.is_dir() and (version_dir / "spec.meta.yaml").exists():
                                ref = f"{cat_dir.name}/{transform_dir.name}@{version_dir.name}"
                                console.print(f"  {ref}")
