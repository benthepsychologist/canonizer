# Changelog

All notable changes to Canonizer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-13

### Added

#### Core Features
- Initial release of Canonizer - Pure JSON transformation tool
- JSONata-based transformation engine with dual runtime support (Node.js + Python)
- Schema validation with Iglu SchemaVer format support
- Transform metadata model with Pydantic validation
- Checksum verification for transform integrity

#### Transform Registry (AIP-canonizer-2025-11-12-001)
- **Git-based transform registry** with HTTP discovery
- **Registry CLI commands:**
  - `can registry list` - List all available transforms
  - `can registry search` - Search by schema URIs, ID, or status
  - `can registry pull` - Download transforms to local cache
  - `can registry info` - Display transform metadata
  - `can registry validate` - Validate transform directories locally
- **Registry client (`RegistryClient`):**
  - Fetch transforms and schemas from GitHub-based registry
  - Local caching at `~/.cache/canonizer/registry/`
  - Automatic checksum verification
  - Index-based efficient discovery
- **Transform validation module:**
  - Directory structure validation
  - Metadata validation with Pydantic
  - Checksum integrity verification
  - Golden test execution
  - Detailed error reporting
- **Official registry** at https://github.com/benthepsychologist/canonizer-registry
  - CI-driven validation on PRs
  - Automatic index generation on merge
  - Initial transform: `email/gmail_to_canonical@1.0.0`

#### CLI Commands
- `can transform run` - Execute JSON transformations
- `can transform list` - List local transforms
- `can validate run` - Validate JSON against schemas
- `can diff run` - Compare schemas and detect changes
- `can patch run` - Apply mechanical updates to transforms

#### Schema Evolution
- Schema differ with change classification (ADD, RENAME, REMOVE, TYPE_CHANGE, COMPLEX)
- Transform patcher for mechanical updates
- Levenshtein distance-based rename detection
- Conservative patching approach (fails safe for complex changes)

#### Documentation
- Comprehensive README with Quick Start guide
- Registry contribution guide (`docs/REGISTRY.md`)
  - Usage instructions for all CLI commands
  - Contribution workflow with examples
  - Versioning policy (SemVer + Iglu SchemaVer)
  - Security and governance model
  - Example workflows
- API documentation with docstrings
- AIP execution summary with full audit trail

### Technical Details

#### Models
- `TransformMeta` - Transform metadata with Pydantic validation
  - `Checksum` model with SHA256 integrity
  - `Provenance` model for authorship tracking
  - `Compat` model for schema version ranges
  - `TestFixture` model for golden tests
- `Transform` - Complete transform with metadata and JSONata source

#### Architecture
- Pure function design (no side effects)
- Portable `.jsonata` files (language-agnostic)
- Minimal `.meta.yaml` sidecars
- Local-first with optional registry
- CLI-first design for composability

### Quality Metrics
- 68 unit and integration tests passing
- 43% overall code coverage (96-100% on registry core modules)
- Ruff linting checks passing
- Type hints with mypy support
- Comprehensive error handling

### Repository Structure
```
canonizer/
├── canonizer/           # Main package
│   ├── cli/            # Typer-based CLI
│   ├── core/           # Transform runtime and evolution
│   └── registry/       # Registry client and validation
├── docs/               # Documentation
├── tests/              # Unit and integration tests
└── transforms/         # Local transform examples
```

### Known Limitations
- CLI commands have 0% test coverage (only manually tested)
- Node.js JSONata runtime requires `npm install jsonata` separately
- Coverage goal of 70% not met (43% overall, but core modules are 96-100%)
- `can registry publish` command not implemented (deferred to v0.2)

### Dependencies
- Python 3.11+
- jsonata-python 0.6+ (Python runtime)
- pydantic 2.5+
- jsonschema 4.20+
- typer 0.9+
- rich 13.7+
- httpx 0.27+
- PyYAML 6.0+

### Migration Notes
This is the initial release. No migration required.

### Credits
- Developed by Ben Machina
- Built with Claude Code (Anthropic Sonnet 4.5)
- Follows AIP (Agentic Implementation Plan) methodology
- Inspired by Snowplow's Iglu schema registry

### Links
- **Main Repository:** https://github.com/benthepsychologist/canonizer
- **Registry Repository:** https://github.com/benthepsychologist/canonizer-registry
- **Documentation:** [docs/REGISTRY.md](docs/REGISTRY.md)
- **AIP:** AIP-canonizer-2025-11-12-001

---

## [0.2.0] - 2025-11-13

### Added

#### Email Canonicalization (AIP-canonizer-2025-11-13-001)
- **6 production email transforms:**
  - `email/gmail_to_jmap_full@1.0.0` - Gmail → JMAP Full (RFC 8621 complete)
  - `email/gmail_to_jmap_lite@1.0.0` - Gmail → JMAP Lite (simplified inline body)
  - `email/gmail_to_jmap_minimal@1.0.0` - Gmail → JMAP Minimal (metadata only)
  - `email/exchange_to_jmap_full@1.0.0` - Exchange → JMAP Full
  - `email/exchange_to_jmap_lite@1.0.0` - Exchange → JMAP Lite
  - `email/exchange_to_jmap_minimal@1.0.0` - Exchange → JMAP Minimal

- **4 new canonical schemas:**
  - `com.microsoft/exchange_email@1-0-0` - Microsoft Graph API Message Resource
  - `org.canonical/email_jmap_full@1-0-0` - RFC 8621 complete (~50-200KB per email)
  - `org.canonical/email_jmap_lite@1-0-0` - Simplified inline body (~10-50KB per email)
  - `org.canonical/email_jmap_minimal@1-0-0` - Metadata only (~1-5KB per email)

- **Comprehensive documentation:**
  - `docs/EMAIL_CANONICALIZATION.md` - Architecture and design decisions
  - Three-tier canonical format strategy (Full/Lite/Minimal)
  - Storage vs. functionality trade-off analysis
  - Use case mapping for each canonical format

- **19 integration tests** covering:
  - Golden test validation for all 6 transforms
  - Invalid input handling
  - Null value handling
  - Schema validation (input and output)
  - Runtime assertions (Node.js JSONata)

### Technical Details
- All transforms use Python jsonata runtime (no Node.js dependency for validation)
- All transforms published to canonizer-registry with CI passing
- Array constructor pattern for JSONata `$map()` single-item compatibility
- Comprehensive email header mapping (from, to, cc, bcc, replyTo, sender)
- Thread tracking support (messageId, inReplyTo, references)
- Attachment handling across all format levels

### Quality Metrics
- 94 total tests passing (up from 68)
- 44% overall code coverage (up from 43%)
- 100% test pass rate for email transforms
- Registry CI validation passing with Python jsonata

## [0.3.0] - 2025-11-17

### Added

#### Dataverse Canonicalization (AIP-canonizer-2025-11-17-001)
- **3 canonical JSON schemas:**
  - `transforms/schemas/canonical/contact_v1-0-0.json` - Contact/person data schema
  - `transforms/schemas/canonical/clinical_session_v1-0-0.json` - Clinical appointment/session schema
  - `transforms/schemas/canonical/report_v1-0-0.json` - Clinical report/document schema

- **3 Dataverse transforms:**
  - `transforms/contact/dataverse_contact_to_canonical_v1.jsonata` - Dataverse Contact → Canonical
  - `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata` - Dataverse Session → Canonical
  - `transforms/report/dataverse_report_to_canonical_v1.jsonata` - Dataverse Report → Canonical

- **Comprehensive governance documentation:**
  - `artifacts/governance/decision-log.md` - 10 design decisions with rationale
  - `artifacts/governance/transform-mappings.md` - Complete field mapping reference for all 3 transforms
  - `artifacts/test/test-pass-confirmation.md` - Test results and validation status

### Technical Details
- **Contact Transform Features:**
  - Standard Dataverse field mapping (contactid, firstname, lastname, etc.)
  - Conditional address object creation (only when data present)
  - Support for email, phone, mobile fields
  - Birth date and timestamp handling

- **Clinical Session Transform Features:**
  - Status code mapping (integer → readable strings: scheduled/completed/cancelled/in_progress/no_show)
  - Fallback handling for field name variations (sessionid/appointmentid)
  - Custom field support with `_ben_` prefix assumption
  - Duration and scheduling metadata

- **Report Transform Features:**
  - Dual entity type support (custom Report entity or standard Annotation entity)
  - Fallback chaining for flexible field mapping
  - Status enumeration (draft/final/amended/archived)
  - Content handling for text and binary documents

- **Design Patterns:**
  - ISO 8601 date/datetime formats for portability
  - GUID string coercion with `$string()` for consistency
  - Source metadata injection (`platform: "dataverse", platform_version: "v1"`)
  - Conditional object creation to avoid empty nested objects

### Quality Metrics
- 94 total tests passing (maintained from v0.2)
- 44% overall code coverage (maintained)
- Ruff linting: All checks passed
- No regressions introduced

### Known Limitations
- No Dataverse sample data available for validation yet (pending tap-dataverse output)
- Field names based on standard Dataverse schema (may need adjustment for custom deployments)
- Test coverage remains at 44% (target: 70%+)
- `.meta.yaml` metadata files deferred until real data validation

### Next Steps
- Validate transforms against real Dataverse data when available from tap-dataverse
- Create `.meta.yaml` metadata files with checksums
- Add integration tests for new transforms
- Consider publishing to canonizer-registry

## [0.4.0] - 2025-11-19

### Added

#### Pure Transformation Library API (AIP-canonizer-2025-11-18-001)

**Major architectural refactor**: Canonizer is now a library-first package with a clean programmatic API.

- **Core API functions:**
  - `canonicalize(raw_document, *, transform_id, ...)` - Pure transformation function
  - `run_batch(documents, *, transform_id, ...)` - Batch processing
  - `canonicalize_email_from_gmail(raw_email, *, format="lite")` - Gmail convenience wrapper
  - `canonicalize_email_from_exchange(raw_email, *, format="lite")` - Exchange convenience wrapper
  - `canonicalize_form_response(raw_form)` - Forms convenience wrapper

- **New module:** `canonizer/api.py` (249 lines, 5 public functions)

- **Comprehensive testing:**
  - 15 new unit tests for API (`tests/unit/test_api.py`)
  - 9 CLI compatibility tests (`tests/integration/test_cli_compat.py`)
  - Total: 115 tests passing (up from 94)

- **Complete documentation:**
  - `docs/API.md` - Complete API reference (221 lines)
  - `examples/basic_usage.py` - Simple usage examples
  - `examples/lorchestra_job.py` - Orchestration pattern for lorchestra integration
  - Updated README with API-first quick start

### Changed

#### Package Architecture
- **Version:** 0.3.0 → 0.4.0
- **Development Status:** Alpha → Beta
- **CLI dependencies (typer, rich) moved to optional `[cli]` extra**
  - `pip install canonizer` - Library only (no CLI)
  - `pip install canonizer[cli]` - With CLI tools
- **Core library now has minimal dependencies** (no typer/rich required)

#### CLI Refactoring
- `canonizer/cli/cmds/transform.py` refactored to use `canonicalize()` API
- CLI is now a thin wrapper around the programmatic API
- All existing CLI commands remain backward compatible
- No breaking changes

### Design Principles

**Pure Function Approach:**
```python
canonical = canonicalize(raw_document, transform_id="email/gmail_to_jmap_lite@1.0.0")
```

**Zero Orchestration Logic:**
- NO event emission
- NO BigQuery queries
- NO job patterns
- Just: `raw_json + transform_id → canonical_json`

**Orchestration happens outside** (in lorchestra, Airflow, etc.):
```python
from canonizer import canonicalize
from lorchestra.stack_clients.event_client import emit_event

for row in bq_client.query("SELECT * FROM raw_events WHERE ..."):
    canonical = canonicalize(row.payload, transform_id="...")
    emit_event("email.canonicalized", payload=canonical)
```

### Quality Metrics
- **115 tests passing** (24 new tests added)
- **46% overall coverage** (exceeds 44% target)
- **93-100% coverage on core modules**
- **82% coverage on new API module**
- **Ruff linting:** All checks passed
- **No regressions:** All existing tests still passing

### Migration Guide

#### Before v0.4.0 (CLI-centric)
```python
from canonizer.core.runtime import TransformRuntime
runtime = TransformRuntime()
result = runtime.execute(meta, input_data)
```

#### After v0.4.0 (Library-first)
```python
from canonizer import canonicalize
canonical = canonicalize(raw_document, transform_id="email/gmail_to_jmap_lite@1.0.0")
```

#### CLI (Unchanged)
```bash
can transform run --meta transforms/... --input email.json --output canonical.json
```

### Technical Details

**Transform ID Resolution:**
- Registry-style: `"email/gmail_to_jmap_lite@1.0.0"`
- Full path: `"transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"`

**Error Handling:**
- `ValidationError` for schema validation failures
- `FileNotFoundError` for missing transforms
- `ValueError` for invalid transform IDs

**Batch Processing:**
```python
from canonizer import run_batch
canonicals = run_batch(raw_emails, transform_id="email/gmail_to_jmap_lite@1.0.0")
```

### Breaking Changes

**None.** This is a backward-compatible enhancement.

### Known Limitations
- CLI commands still have 0% test coverage (integration tests cover CLI behavior)
- API doesn't return execution metadata (execution time, runtime version)
- Async API not yet implemented

### Credits
- Developed by Ben Machina
- Built with Claude Code (Anthropic Sonnet 4.5)
- Follows AIP (Agentic Implementation Plan) methodology

---

## [0.5.0] - 2025-11-27

### Added

#### Local Registry MVP (AIP-canonizer-2025-11-26-001)

**New `.canonizer/` directory model** for project-local schema and transform management.

- **New CLI commands:**
  - `canonizer init [path]` - Initialize a `.canonizer/` directory in a project
  - `canonizer import run --from <registry> "<ref>"` - Import schemas/transforms from a registry
  - `canonizer import list` - List locally imported schemas and transforms

- **New modules:**
  - `canonizer/local/__init__.py` - Local registry module
  - `canonizer/local/config.py` - Configuration models (`CanonizerConfig`, `RegistryConfig`)
  - `canonizer/local/lock.py` - Lock file models (`LockFile`, `SchemaLock`, `TransformLock`)
  - `canonizer/local/resolver.py` - Resolution functions for local registry

- **Resolution functions:**
  - `find_canonizer_root()` - Find `.canonizer/` directory from current path
  - `resolve_schema(iglu_ref)` - Resolve Iglu schema reference to local path
  - `resolve_transform(transform_ref)` - Resolve transform reference to local path
  - `resolve_jsonata(transform_ref)` - Resolve transform reference to JSONata file
  - `parse_iglu_ref(ref)` - Parse Iglu URI format
  - `parse_transform_ref(ref)` - Parse transform reference format

- **Configuration files:**
  - `.canonizer/config.yaml` - Project configuration
  - `.canonizer/lock.json` - Integrity tracking with SHA256 hashes
  - `.canonizer/registry/` - Local copies of schemas and transforms

### Changed

#### API Resolution Priority

The `validate_payload()` and `canonicalize()` functions now use this resolution order:

1. Explicit `schemas_dir` parameter (if provided)
2. Local `.canonizer/registry/` directory (if `.canonizer/` exists)
3. `CANONIZER_REGISTRY_ROOT` environment variable (if set)
4. Current working directory (backward compatibility fallback)

**Example:**
```python
from canonizer import canonicalize

# Automatically uses .canonizer/ if present
canonical = canonicalize(
    raw_email,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)
```

#### New Error Types

- `TransformNotFoundError` - Transform not found in local registry
- `SchemaNotFoundError` - Schema not found in local registry
- `CanonizerRootNotFoundError` - No `.canonizer/` directory found
- `InvalidReferenceError` - Invalid Iglu or transform reference format

### Technical Details

#### Directory Structure

```
project/
├── .canonizer/
│   ├── config.yaml           # Project configuration
│   ├── lock.json             # Integrity tracking
│   ├── .gitignore            # Excludes registry/
│   └── registry/             # Local copies (gitignored)
│       ├── schemas/
│       │   └── com.google/gmail_email/jsonschema/1-0-0.json
│       └── transforms/
│           └── email/gmail_to_jmap_lite/1.0.0/
│               ├── spec.meta.yaml
│               └── spec.jsonata
└── src/
    └── ...
```

#### Config File Format (`.canonizer/config.yaml`)

```yaml
version: "1"
registry:
  mode: local
  root: registry  # Relative to .canonizer/
```

#### Lock File Format (`.canonizer/lock.json`)

```json
{
  "version": "1",
  "updated_at": "2025-11-26T22:50:05.731334+00:00",
  "schemas": {
    "iglu:com.google/gmail_email/jsonschema/1-0-0": {
      "path": "schemas/com.google/gmail_email/jsonschema/1-0-0.json",
      "hash": "sha256:4f0b31b..."
    }
  },
  "transforms": {
    "email/gmail_to_jmap_lite@1.0.0": {
      "path": "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
      "hash": "sha256:0bbdd42..."
    }
  }
}
```

### Quality Metrics

- **186 tests passing** (71 new tests added)
- **57% overall coverage** (up from 46%)
- **93-100% coverage on local modules**
- **Ruff linting:** All checks passed
- **No regressions:** All existing tests still passing

### Migration Guide

#### Before v0.5.0 (Registry-based)

Required `CANONIZER_REGISTRY_ROOT` environment variable or explicit `schemas_dir`:

```python
from canonizer import canonicalize

canonical = canonicalize(
    raw_email,
    transform_id="email/gmail_to_jmap_lite@1.0.0",
    schemas_dir="/path/to/registry/schemas"
)
```

#### After v0.5.0 (Local Registry)

Initialize once per project:

```bash
canonizer init .
canonizer import run --from /path/to/canonizer-registry "email/gmail_to_jmap_lite@1.0.0"
```

Then use without explicit paths:

```python
from canonizer import canonicalize

canonical = canonicalize(
    raw_email,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)
```

### Breaking Changes

**None.** This is a backward-compatible enhancement. All existing code continues to work.

### Known Limitations

- Import command only supports local filesystem registries (not HTTP URLs yet)
- No `canonizer update` command to sync with upstream registry
- No integrity verification on transform execution (planned for v0.6)
- Lock file not automatically updated when transforms change

### Credits

- Developed by Ben Machina
- Built with Claude Code (Anthropic Opus 4.5)
- Follows AIP (Agentic Implementation Plan) methodology

---

## [Unreleased]

### Planned for v0.6
- Remote registry support (`canonizer import --from https://...`)
- Schema freshness checking
- `canonizer update` command to sync with upstream
- Integrity verification on transform execution
- Async API: `async def canonicalize_async(...)`
- Streaming batch API for large datasets
- `can registry publish` - Open PR via GitHub API
- Auto-bump version based on diff/patch
- Compatibility matrix validation
- LLM-assisted transform scaffolding
- Increased CLI test coverage (target: 70%+)
- Calendar event canonicalization
- Additional healthcare data transforms (HL7, FHIR)
- Performance profiling and optimization

---

*This changelog follows the [Keep a Changelog](https://keepachangelog.com/) format.*
