# Canonizer

**Pure JSON transformation tool. No ingestion. No storage. Just transforms.**

The tool that should have come in the box. Transform JSON from source shapes (Gmail, Exchange, QuickBooks) to canonical schemas with versioning, validation, and receipts.

Your orchestrator (Snowplow, Airflow, Dagster) calls Canonizer. Canonizer doesn't call anything.

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
- **Schema validation**: Iglu SchemaVer format (MODEL-REVISION-ADDITION)
- **Runtime engine**: Validate → Transform → Validate
- **Mechanical evolution**: Diff/patch for additive changes + renames
- **Portable**: Raw `.jsonata` files work in any JSONata runtime
- **CLI-first**: `can transform`, `can validate`, `can diff`, `can patch`
- **Integrity**: Checksum verification prevents tampering

## Installation

```bash
# Clone the repo
git clone https://github.com/ben_machina/canonizer.git
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

### 1. Transform JSON data

```bash
# Execute a transform
can transform run \
  --meta transforms/email/gmail_to_canonical.meta.yaml \
  --input sample_gmail.json \
  --output canonical_email.json

# Or use stdin/stdout
cat sample_gmail.json | can transform run --meta transforms/email/gmail_to_canonical.meta.yaml
```

### 2. Validate against schema

```bash
can validate run \
  --schema schemas/org.canonical/email/jsonschema/1-0-0.json \
  --data canonical_email.json
```

### 3. List available transforms

```bash
can transform list --dir transforms/
```

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
- PII redaction policy

### Runtime Flow

```
1. Load .meta.yaml + .jsonata file
2. Verify checksum (prevent tampering)
3. Validate input against from_schema
4. Execute JSONata transform
5. Validate output against to_schema
6. Emit receipt (audit trail)
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

```bash
# Transform
can transform run --meta <meta.yaml> --input <json> --output <json>
can transform list --dir transforms/

# Validate
can validate run --schema <schema.json> --data <json>

# Diff (schema evolution)
can diff run --from <v1.json> --to <v2.json> --output <patch.json>

# Patch (apply mechanical updates)
can patch run --transform <file.jsonata> --patch <patch.json> --output <new.jsonata>

# Scaffold (LLM-assisted generation)
can scaffold --from-schema <json> --to-schema <json> --output-dir transforms/
```

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
id: gmail_to_canonical_email
version: 1-0-0  # Iglu SchemaVer (MODEL-REVISION-ADDITION)
engine: jsonata
runtime: node  # or 'python' for fast path

from: iglu:com.google/gmail_email/jsonschema/1-0-0
to: iglu:org.canonical/email/jsonschema/1-0-0

spec_path: gmail_to_canonical_v1.jsonata  # relative path
checksum: sha256:abc123...  # verify .jsonata file integrity

status: stable
author: ben@example.com
created: 2025-11-09T00:00:00Z

tests:
  - input: ../../tests/golden/email/gmail_v1/input.json
    expect: ../../tests/golden/email/gmail_v1/output.json

redact_fields: [payload.body, payload.attachments]  # PII redaction
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

- **v0.1** (Current): Core runtime, diff/patch, LLM scaffolding
- **v0.2**: Remote transform registry (GitHub-based)
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
- Audit trails and receipts
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
