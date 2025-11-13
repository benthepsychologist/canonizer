---
version: "0.1"
tier: B
title: "Canonizer Registry: Transform & Schema Registry with CI-Driven Validation"
owner: benthepsychologist
goal: "Build Git-based transform registry with PR workflow, CI validation, and HTTP-based discovery"
labels: [registry, transforms, schemas, ci, discovery]
project_slug: canonizer
spec_version: 1.0.0
created: 2025-11-12T20:14:06.580798+00:00
updated: 2025-11-12T20:30:00.000000+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/canonizer-aip-v01-registry"
---

# Canonizer Registry: Transform & Schema Registry (v0.1)

## Executive Summary

Build a **Git-based transform registry** (`canonizer-registry` repo) with:
- **PR-based governance** (no direct CLI push)
- **CI-driven validation** (GitHub Actions validates all contributions)
- **HTTP-based discovery** (REGISTRY_INDEX.json consumed by CLI)
- **Deterministic layout** (boring, stable paths with meaning in metadata)

**Philosophy:** CI is the boss. The client is thin. Git provides provenance, immutability, and review.

---

## Objective

Ship a **public transform registry** that:
1. Stores versioned transforms (.jsonata + .meta.yaml) and schemas (JSON Schema)
2. Validates contributions via CI (checksums, golden tests, schema compliance)
3. Generates a machine-readable index (REGISTRY_INDEX.json) for discovery
4. Supports CLI commands: `list`, `search`, `pull`, `validate`, `publish` (opens PR)

---

## Architecture Decisions

### What to KEEP
- ✅ Transforms as raw `.jsonata` + tiny `.meta.yaml` sidecars
- ✅ Iglu-style SchemaVer for schemas (MODEL-REVISION-ADDITION)
- ✅ Basic `can registry` commands (search/list/pull/publish)
- ✅ Publish goes through **PRs only**, not direct pushes

### What to CUT (for v0.1)
- ❌ Direct CLI push to registry (force PR workflow for review/CI/provenance)
- ❌ Client-side auto-bump logic + compatibility matrices (do in CI instead)
- ❌ Complex version range resolution (start strict, loosen later)

### What to CHANGE
- 🔄 **Registry location:** Separate public repo `canonizer-registry` (not in canonizer code repo)
- 🔄 **Deterministic IDs & layout:** Stable paths, meaning in metadata
- 🔄 **CI as gatekeeper:** All validation, testing, and index generation in GitHub Actions

---

## Registry Structure

### Repository: `canonizer-registry`

```
canonizer-registry/
  LICENSE                       # Apache-2.0
  README.md                     # Contribution guide
  REGISTRY_INDEX.json           # Machine index (CI-generated, DO NOT EDIT)

  transforms/
    email/
      gmail_to_canonical/
        1.0.0/
          spec.jsonata          # Transform logic (source of truth)
          spec.meta.yaml        # Metadata sidecar
          tests/
            input.json          # Golden test input
            expected.json       # Expected output
        1.1.0/
          spec.jsonata
          spec.meta.yaml
          tests/
            input.json
            expected.json
      exchange_to_canonical/
        1.0.0/
          spec.jsonata
          spec.meta.yaml
          tests/
            input.json
            expected.json

  schemas/
    org.canonical/
      email/
        jsonschema/
          1-0-0.json            # Canonical email schema
    com.google/
      gmail_email/
        jsonschema/
          1-0-0.json            # Gmail source schema
    org.microsoft/
      exchange_email/
        jsonschema/
          1-0-0.json            # Exchange source schema

  .github/
    workflows/
      validate.yml              # CI validation + index generation
    PULL_REQUEST_TEMPLATE.md    # Required fields for contributions
    CODEOWNERS                  # Namespace ownership

  tools/
    validate.py                 # Validation script (shared with CLI)
    generate_index.py           # Build REGISTRY_INDEX.json
```

---

## Transform Metadata Sidecar (spec.meta.yaml)

### Minimal Fields for v0.1

```yaml
# Transform identity
id: email/gmail_to_canonical
version: 1.0.0
engine: jsonata

# Schema contracts
from_schema: iglu:com.google/gmail_email/jsonschema/1-0-0
to_schema: iglu:org.canonical/email/jsonschema/1-0-0

# Compatibility (optional, start strict)
compat:
  from_schema_range: "1-0-0 .. 1-2-x"   # Optional Iglu range

# Golden tests (required)
tests:
  - input: tests/input.json
    expect: tests/expected.json

# Integrity
checksum:
  jsonata_sha256: "<hex>"

# Provenance
provenance:
  author: "Ben <ben@example.com>"
  created_utc: "2025-03-01T12:34:56Z"

# Lifecycle
status: stable   # draft | stable | deprecated
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Transform identifier (e.g., `email/gmail_to_canonical`) |
| `version` | string | ✅ | SemVer version (e.g., `1.0.0`) |
| `engine` | string | ✅ | Transform engine (only `jsonata` for v0.1) |
| `from_schema` | string | ✅ | Input schema URI (Iglu format) |
| `to_schema` | string | ✅ | Output schema URI (Iglu format) |
| `compat.from_schema_range` | string | ❌ | Optional Iglu version range for source schema |
| `tests` | array | ✅ | List of golden test fixtures (at least 1 required) |
| `checksum.jsonata_sha256` | string | ✅ | SHA256 hex digest of `spec.jsonata` |
| `provenance.author` | string | ✅ | Author name and email |
| `provenance.created_utc` | string | ✅ | ISO 8601 timestamp (UTC) |
| `status` | enum | ✅ | Lifecycle: `draft`, `stable`, `deprecated` |

---

## REGISTRY_INDEX.json Schema

**CI-generated catalog** consumed by `can registry list/search`.

```json
{
  "version": "1.0.0",
  "generated_at": "2025-11-12T20:30:00Z",
  "transforms": [
    {
      "id": "email/gmail_to_canonical",
      "versions": [
        {
          "version": "1.0.0",
          "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
          "to_schema": "iglu:org.canonical/email/jsonschema/1-0-0",
          "status": "stable",
          "checksum": {
            "jsonata_sha256": "abc123..."
          },
          "path": "transforms/email/gmail_to_canonical/1.0.0/",
          "author": "Ben <ben@example.com>",
          "created_utc": "2025-03-01T12:34:56Z"
        },
        {
          "version": "1.1.0",
          "from_schema": "iglu:com.google/gmail_email/jsonschema/1-0-0",
          "to_schema": "iglu:org.canonical/email/jsonschema/1-1-0",
          "status": "stable",
          "checksum": {
            "jsonata_sha256": "def456..."
          },
          "path": "transforms/email/gmail_to_canonical/1.1.0/",
          "author": "Ben <ben@example.com>",
          "created_utc": "2025-04-15T10:20:30Z"
        }
      ]
    }
  ],
  "schemas": [
    {
      "uri": "iglu:org.canonical/email/jsonschema/1-0-0",
      "path": "schemas/org.canonical/email/jsonschema/1-0-0.json"
    },
    {
      "uri": "iglu:com.google/gmail_email/jsonschema/1-0-0",
      "path": "schemas/com.google/gmail_email/jsonschema/1-0-0.json"
    }
  ]
}
```

---

## CI Validation Rules

### GitHub Actions Workflow (`.github/workflows/validate.yml`)

**Triggers:** PR, push to main

**Jobs:**
1. **Validate Structure**
   - Check directory layout matches spec
   - Verify all required files present (spec.jsonata, spec.meta.yaml, tests/)
   - Validate unique (id, version) tuples (no duplicates)

2. **Validate Metadata**
   - Parse `spec.meta.yaml` with Pydantic/jsonschema
   - Verify `id` matches directory path
   - Verify `version` is valid SemVer
   - Check Iglu schema URIs are well-formed
   - Validate `checksum.jsonata_sha256` matches actual file hash

3. **Validate Transforms**
   - Execute JSONata against `tests/input.json`
   - Compare output to `tests/expected.json` (exact match)
   - Fail if any golden test fails

4. **Validate Schemas**
   - Validate JSON Schema syntax
   - Check referenced schemas exist in registry

5. **Generate Index**
   - Build `REGISTRY_INDEX.json` from validated transforms
   - Commit to main (on merge) or attach as artifact (on PR)

6. **Security Checks**
   - No code execution in transforms (JSONata only)
   - Checksum verification prevents tampering
   - Sandboxed JSONata engine for test execution

---

## Client Commands (canonizer CLI)

### `can registry list`

List all available transforms from registry.

```bash
can registry list
can registry list --status stable
can registry list --refresh   # Force refresh cache
```

**Implementation:**
- Fetch `REGISTRY_INDEX.json` from GitHub raw URL (HTTPS)
- Cache locally at `~/.canonizer/registry/index.json` with TTL (1 hour default)
- Display: id, versions, from_schema, to_schema, status

---

### `can registry search`

Search transforms by schema URIs or keywords.

```bash
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0
can registry search --to iglu:org.canonical/email/jsonschema/1-0-0
can registry search --id email/gmail_to_canonical
can registry search --status stable
```

**Implementation:**
- Filter `REGISTRY_INDEX.json` by provided criteria
- Support multiple filters (AND logic)
- Display matching transforms with version info

---

### `can registry pull <id>@<version>`

Download transform to local cache.

```bash
can registry pull email/gmail_to_canonical@1.0.0
can registry pull email/gmail_to_canonical@latest   # Pull latest stable
```

**Implementation:**
- Fetch `spec.jsonata`, `spec.meta.yaml`, and `tests/` from GitHub raw URLs
- Store in `~/.canonizer/registry/transforms/<id>/<version>/`
- Verify checksum matches metadata
- Can now use with `can transform run --meta ~/.canonizer/registry/...`

---

### `can registry validate <path>`

Run CI validation checks locally.

```bash
can registry validate transforms/email/gmail_to_canonical/1.0.0/
```

**Implementation:**
- Use same validation logic as CI (`tools/validate.py`)
- Check metadata, checksums, golden tests
- Exit 0 if valid, exit 1 with errors if invalid

---

### `can registry publish` (Optional for v0.1)

Open a PR to contribute transform to registry.

```bash
can registry publish transforms/email/my_new_transform/1.0.0/
```

**Implementation:**
- Validate locally first (same as CI)
- Create fork of `canonizer-registry` (if not exists)
- Create branch: `add-<id>-<version>`
- Commit files
- Push to fork
- Open PR via GitHub API with template filled
- User must authenticate with GitHub token (gh CLI or GITHUB_TOKEN env var)

**Deferred to future:** Auto-fill PR template, interactive prompts for missing metadata

---

## Versioning Policy

### Schemas (Iglu SchemaVer: MODEL-REVISION-ADDITION)

| Change Type | Bump | Example |
|-------------|------|---------|
| Breaking change (remove field, change type) | MODEL | `1-0-0` → `2-0-0` |
| Non-breaking change (modify description) | REVISION | `1-0-0` → `1-1-0` |
| Additive change (new optional field) | ADDITION | `1-0-0` → `1-0-1` |

### Transforms (SemVer: MAJOR.MINOR.PATCH)

| Change Type | Bump | Example |
|-------------|------|---------|
| Breaking change (different output schema) | MAJOR | `1.0.0` → `2.0.0` |
| New feature (support new input schema) | MINOR | `1.0.0` → `1.1.0` |
| Bug fix (same I/O, better logic) | PATCH | `1.0.0` → `1.0.1` |

### Compatibility Rules (v0.1: Start Strict)

- Transform declares **exact** `to_schema` (strict output contract)
- Transform declares **exact** `from_schema` by default
- Optional: Declare `compat.from_schema_range` if tested across versions
- Example: `"1-0-0 .. 1-2-x"` means "works with MODEL=1, REVISION=0-2, any ADDITION"

**Future:** Loosen once we have evidence and testing across schema versions.

---

## Security & Governance

### License
- **Registry:** Apache-2.0 (permissive, community-friendly)
- **Transforms:** Contributors retain copyright, but license under Apache-2.0 on contribution

### CODEOWNERS
Assign ownership for critical namespaces:
```
# Canonical schemas require maintainer approval
/schemas/org.canonical/ @ben_machina @canonizer-maintainers

# Email transforms require domain expert review
/transforms/email/ @ben_machina
```

### Pull Request Template

Required fields for all PRs:
```markdown
## Transform Contribution

**Transform ID:** email/my_transform
**Version:** 1.0.0
**From Schema:** iglu:vendor/name/jsonschema/1-0-0
**To Schema:** iglu:org.canonical/name/jsonschema/1-0-0

### Rationale
Why is this transform needed? What use case does it solve?

### Sample Input/Output
Provide a real-world example (anonymized/sanitized).

### Source Schema Link
Link to official vendor API docs or schema definition.

### Checklist
- [ ] Golden tests pass locally (`can registry validate`)
- [ ] No PII in test fixtures
- [ ] Checksum verified
- [ ] Documentation updated (if needed)
```

### Security Requirements
- ❌ **No code execution** in registry (JSONata only, no eval/exec)
- ✅ **Sandboxed execution** in CI (isolated runner, no network access)
- ✅ **Checksum verification** prevents tampering
- ✅ **Review required** (no direct commits to main)
- ✅ **Provenance tracking** (author, timestamp in metadata)

---

## Plan

### Step 1: Registry Repository Setup [G0: Plan Approval]

**Prompt:**

Create the `canonizer-registry` GitHub repository with complete CI infrastructure:
1. Initialize public GitHub repo `canonizer-registry`
2. Add LICENSE (Apache-2.0), README.md, CONTRIBUTING.md
3. Create directory structure: `schemas/`, `transforms/`, `tools/`, `.github/workflows/`
4. Implement `.github/workflows/validate.yml` for CI validation
5. Add `.github/PULL_REQUEST_TEMPLATE.md` and `.github/CODEOWNERS`
6. Implement `tools/validate.py` (Python validation script)
7. Implement `tools/generate_index.py` (builds REGISTRY_INDEX.json)

**Commands:**

```bash
# After creating repo on GitHub
git clone https://github.com/<username>/canonizer-registry
cd canonizer-registry
mkdir -p schemas transforms tools .github/workflows
# Create and commit initial files
git add .
git commit -m "Initial registry setup"
git push origin main
```

**Outputs:**
- `canonizer-registry` repo live and public
- `.github/workflows/validate.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/CODEOWNERS`
- `tools/validate.py`
- `tools/generate_index.py`
- `LICENSE`, `README.md`, `CONTRIBUTING.md`

---

### Step 2: Migrate Existing Schemas & Transforms

**Prompt:**

Populate the registry with initial content:
1. Migrate schemas to registry format:
   - `schemas/org.canonical/email/jsonschema/1-0-0.json`
   - `schemas/com.google/gmail_email/jsonschema/1-0-0.json`
2. Migrate transform with proper structure:
   - `transforms/email/gmail_to_canonical/1.0.0/spec.jsonata`
   - `transforms/email/gmail_to_canonical/1.0.0/spec.meta.yaml`
   - `transforms/email/gmail_to_canonical/1.0.0/tests/input.json`
   - `transforms/email/gmail_to_canonical/1.0.0/tests/expected.json`
3. Generate initial `REGISTRY_INDEX.json` via CI
4. Verify CI validates successfully

**Commands:**

```bash
# Add content and trigger CI
git add schemas/ transforms/
git commit -m "Add initial schemas and transforms"
git push origin main
# Wait for CI to pass and generate REGISTRY_INDEX.json
```

**Outputs:**
- `schemas/org.canonical/email/jsonschema/1-0-0.json`
- `schemas/com.google/gmail_email/jsonschema/1-0-0.json`
- `transforms/email/gmail_to_canonical/1.0.0/*`
- `REGISTRY_INDEX.json` (CI-generated)

---

### Step 3: Update TransformMeta Model [G1: Design Review]

**Prompt:**

Extend the `TransformMeta` Pydantic model in the canonizer CLI to support new registry fields:
1. Add `Compat` model with `from_schema_range` field (optional)
2. Add `Provenance` model with `author` and `created_utc` fields (required)
3. Update `TransformMeta` to include these new fields
4. Add validators for new fields (schema range validation, UTC timestamp)
5. Update all related tests

**Commands:**

```bash
pytest tests/unit/test_transform_meta.py -v
ruff check canonizer/registry/
```

**Outputs:**
- `canonizer/registry/transform_meta.py` (updated)
- `tests/unit/test_transform_meta.py` (updated)

---

### Step 4: Registry Client Core

**Prompt:**

Implement the core registry client library for discovering and fetching transforms:

1. **index.py**: Fetch and cache REGISTRY_INDEX.json
   - Fetch from GitHub raw URL
   - Local cache at `~/.canonizer/registry/index.json` with 1-hour TTL
   - Parse into Pydantic models

2. **remote.py**: HTTPS file fetching
   - Fetch transform files (spec.jsonata, spec.meta.yaml, tests/)
   - Verify checksums after download
   - Handle HTTP errors gracefully

3. **cache.py**: Local cache management
   - Store at `~/.canonizer/registry/transforms/<id>/<version>/`
   - TTL management and refresh logic
   - Cache invalidation

4. **github.py**: GitHub API client (for publish command)
   - Fork repository
   - Create branch, commit files, push
   - Open PR via GitHub API

**Commands:**

```bash
pytest tests/unit/test_index.py tests/unit/test_remote.py tests/unit/test_cache.py -v
ruff check canonizer/registry/
```

**Outputs:**
- `canonizer/registry/index.py`
- `canonizer/registry/remote.py`
- `canonizer/registry/cache.py`
- `canonizer/registry/github.py`
- Unit tests for each module

---

### Step 5: CLI Commands [G2: Code Review]

**Prompt:**

Implement `can registry` CLI commands:

1. `can registry list [--status] [--refresh]`
   - Read cached index, display all transforms
   - Support status filtering (stable/draft/deprecated)
   - Force refresh option

2. `can registry search [--from] [--to] [--id] [--status]`
   - Filter index by schema URIs, ID, or status
   - Support multiple filters (AND logic)

3. `can registry pull <id>@<version>`
   - Download transform to local cache
   - Support `@latest` for latest stable version
   - Verify checksums

4. `can registry validate <path>`
   - Run CI validation checks locally
   - Reuse `tools/validate.py` from registry repo

5. `can registry publish <path>` (optional for v0.1)
   - Validate locally first
   - Open PR to contribute transform

**Commands:**

```bash
# Test CLI commands
can registry list
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0
can registry pull email/gmail_to_canonical@1.0.0
can registry validate ~/.canonizer/registry/transforms/email/gmail_to_canonical/1.0.0/

# Run CLI tests
pytest tests/integration/test_registry_cli.py -v
```

**Outputs:**
- `canonizer/cli/cmds/registry.py`
- `tests/integration/test_registry_cli.py`

---

### Step 6: Validation Script (Shared with CI)

**Prompt:**

Create shared validation logic used by both CLI and CI:

1. Implement `tools/validate.py` in canonizer-registry repo with checks:
   - Directory structure matches spec
   - `spec.meta.yaml` parses and validates (Pydantic)
   - `spec.jsonata` exists and checksum matches metadata
   - Golden tests exist and pass (execute JSONata)
   - Referenced schemas exist in registry
   - Unique (id, version) tuples across registry

2. Copy or reference validation logic in canonizer CLI
   - `canonizer/registry/validator.py`
   - Ensure CLI `can registry validate` uses same logic

**Commands:**

```bash
# In canonizer-registry repo
python tools/validate.py transforms/email/gmail_to_canonical/1.0.0/

# In canonizer CLI
pytest tests/unit/test_validator.py -v
```

**Outputs:**
- `tools/validate.py` (in canonizer-registry repo)
- `canonizer/registry/validator.py` (in canonizer CLI)
- Tests for validation logic

---

### Step 7: Documentation

**Prompt:**

Document the registry workflow and contribution process:

1. Update `canonizer/README.md` with registry section
2. Create `docs/REGISTRY.md` with detailed contribution guide
3. Create `canonizer-registry/README.md` with usage guide
4. Create `canonizer-registry/CONTRIBUTING.md` with PR workflow

Content to include:
- How to search/pull/use transforms
- How to contribute new transforms (PR workflow)
- Versioning policy and compatibility rules
- Security and governance model
- Example workflows (find transform, contribute transform, update transform)

**Outputs:**
- `canonizer/README.md` (updated)
- `docs/REGISTRY.md` (new)
- `canonizer-registry/README.md` (new)
- `canonizer-registry/CONTRIBUTING.md` (new)

---

### Step 8: Comprehensive Testing & Pre-Release Validation [G3: Pre-Release]

**Prompt:**

Implement comprehensive test coverage for registry features:

1. **Unit Tests** (≥80% coverage for registry modules):
   - `tests/unit/test_index.py` - Index parsing and caching
   - `tests/unit/test_cache.py` - Cache management and TTL
   - `tests/unit/test_remote.py` - Remote fetching and checksums
   - `tests/unit/test_transform_meta.py` - Metadata validation

2. **Integration Tests**:
   - End-to-end: search → pull → validate → use transform
   - CI validation script on sample transforms
   - Index generation from sample registry

3. **CLI Tests**:
   - Test each `can registry` command
   - Mock HTTP responses for index/files
   - Error handling and edge cases

**Commands:**

```bash
# Run all tests
pytest tests/ -v --cov=canonizer --cov-report=term-missing

# Check coverage threshold
pytest tests/ -q --cov=canonizer --cov-fail-under=70

# Lint checks
ruff check canonizer/
```

**Outputs:**
- All unit tests passing
- All integration tests passing
- Coverage report (≥70% overall, ≥80% for registry modules)
- Ruff checks passing

---

## Acceptance Criteria

### Registry Repository
- ✅ `canonizer-registry` repo public and accessible
- ✅ CI validates PRs (structure, metadata, golden tests)
- ✅ CI generates `REGISTRY_INDEX.json` on merge to main
- ✅ At least 1 transform example (gmail_to_canonical/1.0.0)
- ✅ LICENSE (Apache-2.0), CODEOWNERS, PR template in place

### Canonizer Client
- ✅ `can registry list` - Shows all transforms from index
- ✅ `can registry search` - Filters by schema URIs
- ✅ `can registry pull <id>@<version>` - Downloads to cache
- ✅ `can registry validate <path>` - Runs CI checks locally
- ✅ Local cache at `~/.canonizer/registry/` with TTL
- ✅ Checksum verification on pull

### Metadata Model
- ✅ Updated `TransformMeta` with `compat` and `provenance`
- ✅ Pydantic validation passes
- ✅ Tests updated and passing

### Documentation
- ✅ `docs/REGISTRY.md` - Contribution guide
- ✅ `README.md` updated with registry workflow
- ✅ `canonizer-registry/README.md` - Usage guide

### Testing
- ✅ All tests passing (pytest)
- ✅ Coverage ≥70% overall
- ✅ Integration tests for pull → validate → use workflow
- ✅ Ruff checks pass
- ✅ Mypy type checks pass

### Optional (Deferred to v0.2)
- ⏸️ `can registry publish` (opens PR via GitHub API)
- ⏸️ Auto-bump version based on diff/patch
- ⏸️ Compatibility matrix validation

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| CI validation too slow | PRs blocked | Parallelize jobs, cache dependencies |
| Index generation fails | Discovery broken | Validate index schema in CI, rollback on error |
| Checksum mismatch attack | Tampered transforms | CI enforces checksums, git provides provenance |
| Namespace conflicts | Duplicate IDs | CODEOWNERS + unique (id, version) validation |
| Breaking schema changes | Transforms break | SemVer policy + compatibility ranges |

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1. Registry repo setup | 2 days | None |
| 2. Migrate content | 1 day | Phase 1 |
| 3. Update TransformMeta | 1 day | None |
| 4. Registry client core | 3 days | Phase 2, 3 |
| 5. CLI commands | 2 days | Phase 4 |
| 6. Validation script | 1 day | Phase 2 |
| 7. Documentation | 1 day | Phase 5 |
| 8. Testing | 2 days | Phase 5, 6 |
| **Total** | **~2 weeks** | |

---

## Success Metrics

### v0.1 Success Criteria
1. **Discoverability:** Can find transforms via `can registry search`
2. **Usability:** Can pull and use transform in <5 commands
3. **Quality:** CI catches 100% of invalid contributions
4. **Governance:** All contributions reviewed via PR
5. **Adoption:** At least 3 transforms in registry (Gmail, Exchange, 1 other)

### Future Metrics (v0.2+)
- Number of community contributions
- Transform usage stats (download counts)
- Schema version coverage (transforms per schema version)

---

## Open Questions

1. **GitHub org or personal repo?** → Start with personal, migrate to org if needed
2. **Rate limiting on GitHub raw URLs?** → Add retry logic, consider CDN if needed
3. **Versioned index (REGISTRY_INDEX.json)?** → Start unversioned, add versioning if needed
4. **Support multiple registries?** → Start with single canonical, add config later
5. **Private transforms?** → Out of scope for v0.1 (public registry only)

---

## References

- [Iglu Schema Registry](https://github.com/snowplow/iglu)
- [JSONata Specification](https://docs.jsonata.org/)
- [SemVer 2.0.0](https://semver.org/)
- [Apache-2.0 License](https://www.apache.org/licenses/LICENSE-2.0)

---

## Appendix: Example Workflows

### Workflow 1: Find and Use Transform

```bash
# Search for Gmail transforms
can registry search --from iglu:com.google/gmail_email/jsonschema/1-0-0

# Pull specific version
can registry pull email/gmail_to_canonical@1.0.0

# Use the transform
can transform run \
  --meta ~/.canonizer/registry/transforms/email/gmail_to_canonical/1.0.0/spec.meta.yaml \
  --input gmail_message.json \
  --output canonical_email.json
```

### Workflow 2: Contribute New Transform

```bash
# Create local transform
mkdir -p transforms/crm/salesforce_to_canonical/1.0.0/tests
vim transforms/crm/salesforce_to_canonical/1.0.0/spec.jsonata
vim transforms/crm/salesforce_to_canonical/1.0.0/spec.meta.yaml

# Validate locally
can registry validate transforms/crm/salesforce_to_canonical/1.0.0/

# (Optional) Publish via PR
can registry publish transforms/crm/salesforce_to_canonical/1.0.0/

# Or manually: fork canonizer-registry, commit, open PR
```

### Workflow 3: Update Transform for New Schema Version

```bash
# Pull existing transform
can registry pull email/gmail_to_canonical@1.0.0

# Copy to new version
cp -r ~/.canonizer/registry/transforms/email/gmail_to_canonical/1.0.0 \
      transforms/email/gmail_to_canonical/1.1.0/

# Edit for new schema
vim transforms/email/gmail_to_canonical/1.1.0/spec.jsonata
vim transforms/email/gmail_to_canonical/1.1.0/spec.meta.yaml

# Update version and to_schema in metadata
# Bump version: 1.0.0 → 1.1.0 (MINOR bump for new output schema)

# Validate and contribute
can registry validate transforms/email/gmail_to_canonical/1.1.0/
can registry publish transforms/email/gmail_to_canonical/1.1.0/
```

---

**End of Specification**
