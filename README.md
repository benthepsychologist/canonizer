# Canonizer

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/benthepsychologist/canonizer/releases)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Registry](https://img.shields.io/badge/registry-official-green.svg)](https://github.com/benthepsychologist/canonizer-registry)

**Pure JSON transformation tool. No ingestion. No storage. Just transforms.**

The tool that should have come in the box. Transform JSON from source shapes (Gmail, Exchange, QuickBooks) to canonical schemas with versioning and validation.

Your orchestrator (Snowplow, Airflow, Dagster) calls Canonizer. Canonizer doesn't call anything.

📖 **[Changelog](CHANGELOG.md)** | 🔧 **[Registry Guide](docs/REGISTRY.md)** | 📦 **[Registry](https://github.com/benthepsychologist/canonizer-registry)**

## What is Canonizer?

Canonizer is a **pure function** that transforms JSON:

```python
def canonizer(input_json: dict, transform: str) -> dict:
    """Validate → Transform → Validate → Return"""
    return transformed_json
```

It fills the gap between **schema registries** (Iglu) and **data pipelines** (Airbyte/dbt) by managing semantic JSON transforms with versioning and mechanical evolution.

### What it does

```
┌─────────────────────────────────────┐
│  YOUR ORCHESTRATOR                  │
│  (Snowplow, Airflow, etc.)          │
└─────────────────────────────────────┘
            │
            │ 1. Load source JSON
            ↓
┌─────────────────────────────────────┐
│  CANONIZER                          │
│  ├─ Validate input                  │
│  ├─ Transform (JSONata)             │
│  ├─ Validate output                 │
│  └─ Return JSON + Receipt           │
└─────────────────────────────────────┘
            │
            │ 2. Save canonical JSON
            ↓
┌─────────────────────────────────────┐
│  YOUR STORAGE                       │
│  (wherever you want)                │
└─────────────────────────────────────┘
```

**Canonizer only does the middle part.** No ingestion. No storage. No orchestration.

### Key Features

- **Transform registry**: Versioned `.jsonata` files with minimal `.meta.yaml` sidecars
- **Remote registry client**: Fetch transforms from Git-based registries with caching
- **Schema validation**: Iglu SchemaVer format (MODEL-REVISION-ADDITION)
- **Runtime engine**: Validate → Transform → Validate
- **Mechanical evolution**: Diff/patch for additive changes + renames
- **Portable**: Raw `.jsonata` files work in any JSONata runtime
- **CLI-first**: `can transform`, `can validate`, `can diff`, `can patch`, `can registry`
- **Integrity**: SHA256 checksum verification prevents tampering

## Installation

```bash
# Clone the repo
git clone https://github.com/benthepsychologist/canonizer.git
cd canonizer

# Install with uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or with pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

### 1. Use transforms from the registry

The easiest way to get started is using the official registry:

```bash
# List available transforms
can registry list

# Search for transforms by schema
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0

# Get details about a transform
can registry info email/gmail_to_canonical@latest

# Pull a transform to local cache
can registry pull email/gmail_to_canonical@1.0.0

# Use the pulled transform
can transform run \
  --meta ~/.cache/canonizer/registry/.../email/gmail_to_canonical/1.0.0/spec.meta.yaml \
  --input sample_gmail.json \
  --output canonical_email.json
```

### 2. Transform JSON data locally

```bash
# Execute a local transform
can transform run \
  --meta transforms/email/gmail_to_canonical.meta.yaml \
  --input sample_gmail.json \
  --output canonical_email.json

# Or use stdin/stdout
cat sample_gmail.json | can transform run --meta transforms/email/gmail_to_canonical.meta.yaml
```

### 3. Validate against schema

```bash
can validate run \
  --schema schemas/org.canonical/email/jsonschema/1-0-0.json \
  --data canonical_email.json
```

### 4. Use the Python API

```python
from canonizer.registry import RegistryClient

# Initialize client (uses official registry by default)
client = RegistryClient()

# List available transforms
transforms = client.list_transforms()
for t in transforms:
    print(f"{t['id']}: {t['versions'][0]['version']}")

# Fetch a transform
transform = client.fetch_transform("email/gmail_to_canonical")
print(transform.meta.version)  # "1.0.0"
print(transform.jsonata)  # JSONata source code

# Fetch a schema
schema = client.fetch_schema("iglu:org.canonical/email/jsonschema/1-0-0")
```

## Transform Registry

Canonizer includes a **Git-based transform registry** for discovering and sharing transforms.

### Official Registry

**Repository:** https://github.com/benthepsychologist/canonizer-registry

The official registry provides:
- Versioned transforms with checksums
- CI-driven validation
- Community contributions via PR
- HTTP-based discovery

### Using the Registry

```bash
# Discover transforms
can registry list
can registry search --to iglu:org.canonical/email/jsonschema/1-0-0

# Pull and use a transform
can registry pull email/gmail_to_canonical@1.0.0
can transform run --meta ~/.cache/canonizer/registry/.../spec.meta.yaml --input in.json

# Validate before contributing
can registry validate my_transform/1.0.0/
```

### Contributing Transforms

See [`docs/REGISTRY.md`](docs/REGISTRY.md) for the complete contribution guide.

**Quick steps:**
1. Create transform directory: `transforms/<domain>/<id>/<version>/`
2. Add `spec.jsonata` and `spec.meta.yaml`
3. Add golden tests in `tests/`
4. Validate locally: `can registry validate <path>`
5. Open PR to [canonizer-registry](https://github.com/benthepsychologist/canonizer-registry)

## Architecture

### Transform Files

**`.jsonata` files** (source of truth)
- Portable, diffable, language-agnostic
- Works in any JSONata runtime
- ASCII filenames: `[a-z0-9_]+`

**`.meta.yaml` sidecars** (minimal metadata)
- Transform ID, version (Iglu SchemaVer)
- Input/output schema URIs
- Checksum verification
- Test fixtures (golden files)

### Runtime Flow

```
1. Load .meta.yaml + .jsonata file
2. Verify checksum (prevent tampering)
3. Validate input against from_schema
4. Execute JSONata transform
5. Validate output against to_schema
6. Return transformed JSON
```

### Transform Evolution

**Tier 1: Diff/Patch (mechanical)**
- Schema adds optional field → Auto-patch transform
- Schema renames field → Auto-rename in transform
- 80% of changes covered

**Tier 2: LLM Scaffolding (complex)**
- Type changes, structural rewrites
- Generate new transform from schemas
- Human review required

## CLI Commands (`can`)

### Transform Commands
```bash
# Execute a transform
can transform run --meta <meta.yaml> --input <json> --output <json>

# List local transforms
can transform list --dir transforms/
```

### Validation Commands
```bash
# Validate JSON against schema
can validate run --schema <schema.json> --data <json>
```

### Registry Commands
```bash
# List all available transforms
can registry list [--status stable] [--refresh]

# Search for transforms
can registry search --from <schema-uri>      # By input schema
can registry search --to <schema-uri>        # By output schema
can registry search --id <transform-id>      # By ID
can registry search --status stable          # By status

# Get transform information
can registry info <id>@<version>             # Specific version
can registry info <id>@latest                # Latest version

# Pull transform to local cache
can registry pull <id>@<version>
can registry pull email/gmail_to_canonical@1.0.0

# Validate transform directory
can registry validate <path>
can registry validate transforms/email/my_transform/1.0.0/
```

### Schema Evolution Commands
```bash
# Compare schemas and detect changes
can diff run --from <v1.json> --to <v2.json> --output <patch.json>

# Apply mechanical updates to transforms
can patch run --transform <file.jsonata> --patch <patch.json> --output <new.jsonata>
```

See [`docs/REGISTRY.md`](docs/REGISTRY.md) for detailed registry documentation.

## Transform Structure

Transforms live in a simple directory structure:

```
transforms/email/
  gmail_to_canonical_v1.jsonata       # JSONata transform (source of truth)
  gmail_to_canonical_v1.meta.yaml     # Metadata sidecar

schemas/
  com.google/gmail_email/jsonschema/1-0-0.json
  org.canonical/email/jsonschema/1-0-0.json

tests/golden/email/
  gmail_v1/
    input.json
    output.json
```

## Example Transform Metadata

`.meta.yaml` sidecars are minimal and portable:

```yaml
id: email/gmail_to_canonical
version: 1.0.0  # SemVer (MAJOR.MINOR.PATCH)
engine: jsonata
runtime: python  # or 'node' for official JSONata

from_schema: iglu:com.google/gmail_email/jsonschema/1-0-0
to_schema: iglu:org.canonical/email/jsonschema/1-0-0

spec_path: spec.jsonata  # relative path to transform

checksum:
  jsonata_sha256: abc123...  # SHA256 hex digest for integrity

provenance:
  author: "Ben Machina <ben@therapyai.com>"
  created_utc: "2025-11-09T00:00:00Z"

status: stable  # draft, stable, or deprecated

tests:
  - input: ../../tests/golden/email/gmail_v1/input.json
    expect: ../../tests/golden/email/gmail_v1/output.json
```

## Example JSONata Transform

`.jsonata` files contain pure transform logic:

```jsonata
{
  "message_id": payload.id,
  "subject": payload.payload.headers[name="Subject"].value,
  "from": payload.payload.headers[name="From"].value,
  "to": payload.payload.headers[name="To"].value,
  "received_at": $toMillis(payload.internalDate)
}
```

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest --cov=canonizer --cov-report=term-missing

# Lint & format
ruff check .
ruff format .

# Type checking
mypy canonizer/
```

## Roadmap

- **v0.1** (Current): Core runtime, diff/patch, remote registry client
- **v0.2**: LLM scaffolding for complex transforms
- **v0.3**: Schema compatibility checks and migration tools
- **v0.4**: Multi-engine support (jq, Python transforms)
- **v0.5**: Performance optimization (batch transforms)
- **v1.0**: Production-ready with monitoring hooks

## Philosophy

**A pure function, not a pipeline.**

- ✅ **Only transforms** - No ingestion, no storage, no orchestration
- ✅ **Pure function** - JSON in → JSON out, that's it
- ✅ **Portable** - `.jsonata` files work in any JSONata runtime
- ✅ **Minimal metadata** - `.meta.yaml` sidecars, no vendor lock-in
- ✅ **Diff/patch first** - Deterministic beats probabilistic
- ✅ **Versioned** - Iglu SchemaVer (MODEL-REVISION-ADDITION)
- ✅ **Integrity** - Checksum verification prevents tampering
- ✅ **Simple** - Solo developers can use it, production can trust it

**Your orchestrator (Snowplow/Airflow/Dagster) handles:**
- Data ingestion
- Storage and persistence
- Scheduling and retries
- Monitoring and alerting
- Audit trails and logging
- PII handling and redaction

**Canonizer handles:**
- JSON transformation
- Schema validation
- Version management
- Checksum integrity

## Contributing

Contributions welcome! Areas where help is needed:
- Transform examples (Notion, Airtable, QuickBooks, etc.)
- Schema definitions (canonical contracts for common domains)
- Documentation and tutorials
- Testing and validation

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- JSONata (transform DSL)
- Pydantic, Typer, Rich (Python tooling)
- Iglu SchemaVer (schema versioning)

Fills the gap between schema registries (Iglu) and data pipelines (Airbyte/dbt).

---

**Status:** Alpha (v0.1) - Active development, breaking changes expected

**Built by:** [Ben Machina](https://github.com/ben_machina)
