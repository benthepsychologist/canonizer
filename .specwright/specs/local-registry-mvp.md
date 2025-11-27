---
version: "0.1"
tier: C
title: Local Registry MVP
owner: benthepsychologist
goal: Implement local .canonizer/ directory model with schema/transform resolution, deferring remote registry to follow-up spec
labels: [registry, local, mvp, architecture]
project_slug: canonizer
spec_version: 0.1.0
created: 2025-11-26T00:00:00+00:00
updated: 2025-11-26T00:00:00+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/local-registry-mvp"
---

# Local Registry MVP

## Objective

> Implement the local `.canonizer/` directory model and resolution logic.
> This decouples canonizer from requiring a full registry repo clone.
> Remote registry (pull/sync from CDN) is deferred to a follow-up spec.

## Context

### Problem

Currently canonizer requires either:
- `CANONIZER_REGISTRY_ROOT` pointing to a full registry repo clone
- Running from CWD inside the registry repo

This is brittle and doesn't scale to multiple consumers.

### Solution

Each project that uses canonizer gets a `.canonizer/` directory:
```
myproject/
├── .canonizer/
│   ├── config.yaml          # Registry config (local mode for now)
│   ├── lock.json            # Pinned refs + hashes (committed)
│   └── registry/            # Actual files (gitignored)
│       ├── schemas/
│       │   └── com.google/
│       │       └── gmail_email/
│       │           └── jsonschema/
│       │               └── 1-0-0.json
│       └── transforms/
│           └── email/
│               └── gmail_to_jmap_lite/
│                   └── 1.0.0/
│                       ├── spec.meta.yaml
│                       └── spec.jsonata
└── ...
```

## Acceptance Criteria

- [ ] `canonizer init` creates `.canonizer/` directory structure
- [ ] `config.yaml` format defined (local mode only for now)
- [ ] `lock.json` format defined (refs + paths + hashes)
- [ ] `resolve_schema(schema_ref, canonizer_root)` implemented
- [ ] `resolve_transform(transform_ref, canonizer_root)` implemented
- [ ] `validate_payload()` uses local resolution
- [ ] `canonicalize()` uses local resolution
- [ ] No more CWD or env var dependency for path resolution

## Scope

### In Scope (This Spec)

1. **`canonizer init` command**
   - Creates `.canonizer/` directory
   - Creates `config.yaml` with local mode defaults
   - Creates empty `lock.json`
   - Creates `registry/schemas/` and `registry/transforms/` directories

2. **Local resolution functions**
   ```python
   def resolve_schema(schema_ref: str, canonizer_root: Path) -> Path:
       """
       iglu:com.google/gmail_email/jsonschema/1-0-0
       → .canonizer/registry/schemas/com.google/gmail_email/jsonschema/1-0-0.json
       """

   def resolve_transform(transform_ref: str, canonizer_root: Path) -> Path:
       """
       transform:email/gmail_to_jmap_lite/1.0.0
       → .canonizer/registry/transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml
       """
   ```

3. **Config file format**
   ```yaml
   # .canonizer/config.yaml
   registry:
     mode: local
     root: .canonizer/registry
   ```

4. **Lock file format**
   ```json
   {
     "schemas": {
       "iglu:com.google/gmail_email/jsonschema/1-0-0": {
         "path": "schemas/com.google/gmail_email/jsonschema/1-0-0.json",
         "hash": "sha256:abc123..."
       }
     },
     "transforms": {
       "transform:email/gmail_to_jmap_lite/1.0.0": {
         "path": "transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml",
         "hash": "sha256:def456..."
       }
     }
   }
   ```

5. **Wire existing API to use local resolution**
   - `validate_payload()` → uses `resolve_schema()`
   - `canonicalize()` → uses `resolve_transform()` and `resolve_schema()`

### Out of Scope (Deferred to Remote Registry Spec)

- Remote registry endpoint (static host / CDN)
- `canonizer registry pull <ref>` (remote fetching)
- `canonizer registry sync` (sync from remote)
- Git-aware registry operations
- PR/submit tooling for adding schemas
- Hash verification enforcement
- Channel/stability tiers (stable, beta, etc.)

## Plan

### Step 1: Define File Formats [G0: Plan Approval]

**Prompt:**

Define the config.yaml and lock.json file formats with Pydantic models for validation.

**Outputs:**
- `canonizer/local/config.py` - Config model
- `canonizer/local/lock.py` - Lock file model
- `tests/unit/test_local_config.py`

---

### Step 2: Implement `canonizer init` Command [G1: Code Readiness]

**Prompt:**

Create the `canonizer init` CLI command that sets up the `.canonizer/` directory structure.

**Commands:**
```bash
canonizer init
pytest tests/unit/test_cli_init.py -v
```

**Outputs:**
- `canonizer/cli/cmds/init.py`
- `tests/unit/test_cli_init.py`

---

### Step 3: Implement Resolution Functions [G1: Code Readiness]

**Prompt:**

Create resolution functions that convert schema/transform refs to local paths.

```python
def resolve_schema(schema_ref: str, canonizer_root: Path) -> Path
def resolve_transform(transform_ref: str, canonizer_root: Path) -> Path
def find_canonizer_root(start_path: Path) -> Path
```

**Commands:**
```bash
pytest tests/unit/test_resolver.py -v
```

**Outputs:**
- `canonizer/local/resolver.py`
- `tests/unit/test_resolver.py`

---

### Step 4: Wire API Functions [G2: Pre-Release]

**Prompt:**

Update `validate_payload()` and `canonicalize()` to use local resolution when `.canonizer/` exists.

Maintain backward compatibility:
- If explicit `schemas_dir` passed, use it
- Else if `.canonizer/` found, use local resolution
- Else fall back to current behavior

**Commands:**
```bash
pytest tests/unit/test_api.py -v
pytest tests/integration/test_local_registry.py -v
```

**Outputs:**
- `canonizer/api.py` (updated)
- `tests/integration/test_local_registry.py`

---

### Step 5: Manual Population Helper [G2: Pre-Release]

**Prompt:**

Create a helper command or script to copy schemas/transforms from a registry repo clone into `.canonizer/`.

```bash
canonizer import --from /path/to/canonizer-registry --ref iglu:com.google/gmail_email/jsonschema/1-0-0
```

**Outputs:**
- `canonizer/cli/cmds/import_cmd.py`
- Documentation in README

## Future Work (Remote Registry Spec)

When we need remote registry:

1. **Static file hosting**
   - GitHub Pages, Cloudflare R2, S3+CloudFront
   - `GET /schemas/com.google/gmail_email/jsonschema/1-0-0.json`
   - ETag/Last-Modified for caching

2. **`canonizer registry pull <ref>`**
   - Fetch single schema or transform
   - Add to lock.json
   - Store in `.canonizer/registry/`

3. **`canonizer registry sync`**
   - Read lock.json
   - Fetch all declared dependencies
   - Verify hashes

4. **Registry repo CI**
   - Validate schemas on PR
   - Publish to static host on merge
   - Generate index files

## Notes

- This spec is a prerequisite for lorchestra email-canonization spec
- Unblocks validation without requiring full registry clone
- Architecture is forward-compatible with remote registry
