---
version: "0.1"
tier: C
title: Refactor Canonizer to Pure Transform Library
owner: benthepsychologist
goal: Transform Canonizer from CLI tool to pure JSON transformation library with programmatic API
labels: [refactor, architecture, api-design]
project_slug: canonizer
spec_version: 1.0.0
created: 2025-11-18T17:32:48.098628+00:00
updated: 2025-11-18T17:32:48.098628+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/pure-transform-api"
---

# Refactor Canonizer to Pure Transform Library

## Objective

> Transform Canonizer from a CLI tool into a pure JSON transformation library with a clean programmatic API: `raw_json + transform_id → canonical_json`. No event emission, no BigQuery, no orchestration - just transforms.

## Acceptance Criteria

- [ ] CI green (lint + unit tests passing)
- [ ] Core API implemented: `canonicalize(raw_document, transform_id)` returns canonical dict
- [ ] Batch API implemented: `run_batch(docs, transform_id)` returns list of canonical dicts
- [ ] Convenience functions: `canonicalize_email_from_gmail()`, `canonicalize_form_response()`
- [ ] All existing unit tests still pass (no regression)
- [ ] New integration tests for API functions (≥5 tests)
- [ ] Test coverage maintained at ≥44% overall (core modules at 90%+)
- [ ] CLI remains functional as thin wrapper (backward compatibility)
- [ ] `pyproject.toml` updated to separate CLI dependencies
- [ ] Documentation updated: README with API examples, API reference docs

## Context

### Background

**Current State:**
Canonizer is a CLI tool with internal `TransformRuntime` class:
```bash
can transform run --meta transforms/email/gmail.meta.yaml --input email.json --output canonical.json
```

**The Problem:**
- No clean programmatic API - must invoke CLI or directly instantiate `TransformRuntime`
- CLI-centric design makes library usage awkward
- lorchestra needs to call Canonizer as a library, not subprocess
- Mixing orchestration concerns (events, BQ) with transformation logic is a mistake

**The Solution:**

Create a **pure transformation library** with zero orchestration concerns:

**Core principle:** `raw_json + transform_id → canonical_json`

Canonizer should ONLY:
- Load transforms (JSONata files + metadata)
- Validate input against source schema
- Execute transformation
- Validate output against canonical schema
- Return transformed JSON

Canonizer should NOT:
- Know about BigQuery
- Know about events or event envelopes
- Emit events
- Query databases
- Handle orchestration logic

**Orchestration happens outside** (in lorchestra jobs):
```python
# lorchestra job (NOT in canonizer)
from canonizer import canonicalize
from lorchestra.stack_clients.event_client import emit_event

def canonicalize_email_from_events(bq_client, ...):
    # 1. Query raw events from BQ
    rows = bq_client.query("SELECT * FROM raw_events WHERE event_type = 'email.gmail.raw'")

    # 2. Transform each (pure function call)
    for row in rows:
        canonical = canonicalize(row["payload"], transform_id="email/gmail_to_jmap_lite@1.0.0")

        # 3. Emit canonical event
        emit_event("email.canonicalized", payload=canonical, ...)
```

### Constraints

- **No breaking changes to core logic**: `core/runtime.py`, `core/validator.py`, `core/jsonata_exec.py` remain unchanged
- **Backward compatibility**: Existing CLI must continue to work as thin wrapper
- **No new external dependencies**: Use existing stack (pydantic, jsonschema, jsonata-python)
- **Test coverage**: Maintain current 44% overall (core modules at 90%+)
- **Protected paths**: No edits to `schemas/`, `transforms/` directories (data, not code)
- **NO orchestration logic**: No events, no BQ, no event_client, no job patterns

## Plan

### Step 1: Create Core API Module [G0: Plan Approval]

**Prompt:**

Create `canonizer/api.py` with pure transformation functions:

**Core API:**
```python
def canonicalize(
    raw_document: dict,
    *,
    transform_id: str,
    schemas_dir: str | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> dict:
    """
    Transform raw JSON to canonical format.

    Args:
        raw_document: Source JSON document
        transform_id: Transform to use (e.g., "email/gmail_to_jmap_lite@1.0.0")
        schemas_dir: Schema directory (default: "schemas")
        validate_input: Validate against source schema
        validate_output: Validate against canonical schema

    Returns:
        Canonical JSON document

    Raises:
        ValidationError: If validation fails
        TransformError: If transformation fails
    """
    # Use existing TransformRuntime internally
    ...

def run_batch(
    documents: list[dict],
    *,
    transform_id: str,
    schemas_dir: str | None = None,
) -> list[dict]:
    """Transform multiple documents."""
    return [canonicalize(doc, transform_id=transform_id, schemas_dir=schemas_dir) for doc in documents]
```

**Convenience functions:**
```python
def canonicalize_email_from_gmail(raw_email: dict, *, format: str = "lite") -> dict:
    """Gmail API message → JMAP canonical."""
    transform_id = f"email/gmail_to_jmap_{format}@1.0.0"
    return canonicalize(raw_email, transform_id=transform_id)

def canonicalize_email_from_exchange(raw_email: dict, *, format: str = "lite") -> dict:
    """Exchange Graph API message → JMAP canonical."""
    transform_id = f"email/exchange_to_jmap_{format}@1.0.0"
    return canonicalize(raw_email, transform_id=transform_id)

def canonicalize_form_response(raw_form: dict) -> dict:
    """Google Forms response → canonical form_response."""
    return canonicalize(raw_form, transform_id="forms/google_forms_to_canonical@1.0.0")
```

**Commands:**

```bash
ruff check canonizer/api.py
pytest tests/unit/test_api.py -v
```

**Outputs:**

- `canonizer/api.py`
- `canonizer/__init__.py` (export main functions)
- `tests/unit/test_api.py`

---

### Step 2: Refactor CLI to Use API [G1: Code Readiness]

**Prompt:**

Update CLI to be a thin wrapper around the new API:

**Old CLI logic:**
```python
runtime = TransformRuntime()
result = runtime.execute(meta, input_data)
```

**New CLI logic:**
```python
from canonizer import canonicalize
canonical = canonicalize(input_data, transform_id=infer_from_meta(meta))
```

CLI should:
1. Read JSON file(s)
2. Call `canonicalize()` or `run_batch()`
3. Write JSON file(s)
4. Handle exceptions and format error messages

**Commands:**

```bash
pytest tests/integration/test_cli*.py -v
can transform run --meta transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml --input tests/golden/email/gmail_v1/input.json
```

**Outputs:**

- `canonizer/cli/cmds/transform.py` (updated)
- `tests/integration/test_cli_compat.py`

---

### Step 3: Documentation & Examples [G2: Pre-Release]

**Prompt:**

Update all documentation to show API-first usage:

**README.md** - Add programmatic usage section:
```python
# Simple usage
from canonizer import canonicalize

canonical = canonicalize(
    raw_gmail_message,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)

# Convenience functions
from canonizer import canonicalize_email_from_gmail

canonical = canonicalize_email_from_gmail(raw_gmail_message, format="lite")

# Batch processing
from canonizer import run_batch

canonicals = run_batch(raw_emails, transform_id="email/gmail_to_jmap_lite@1.0.0")
```

**docs/API.md** - Complete API reference with all functions

**examples/basic_usage.py** - Simple examples

**examples/lorchestra_job.py** - Show how lorchestra job would use canonizer:
```python
# In lorchestra job (separate package/repo)
from canonizer import canonicalize
from lorchestra.stack_clients.event_client import emit_event
from google.cloud import bigquery

def canonicalize_email_from_events():
    bq = bigquery.Client()
    rows = bq.query("SELECT * FROM raw_events WHERE event_type = 'email.gmail.raw'").result()

    for row in rows:
        canonical = canonicalize(row.payload, transform_id="email/gmail_to_jmap_lite@1.0.0")
        emit_event("email.canonicalized", payload=canonical)
```

**Commands:**

```bash
python examples/basic_usage.py
python examples/lorchestra_job.py  # Should fail (no lorchestra), but validate imports
```

**Outputs:**

- `README.md` (updated)
- `docs/API.md`
- `examples/basic_usage.py`
- `examples/lorchestra_job.py`
- `CHANGELOG.md` (updated)

---

### Step 4: Package Config & Final Validation [G3: Pre-Release]

**Prompt:**

Update package configuration and run full validation:

1. **pyproject.toml** - Move CLI deps to optional, bump to 0.4.0
2. Export main API from `canonizer/__init__.py`
3. Run full test suite
4. Verify package installs correctly

**Commands:**

```bash
pytest tests/ -v --cov=canonizer --cov-report=term-missing
pip install -e .  # No CLI deps
pip install -e ".[cli]"  # With CLI
ruff check .
```

**Outputs:**

- `pyproject.toml` (updated)
- `canonizer/__init__.py` (exports: canonicalize, run_batch, canonicalize_email_from_gmail, etc.)
- `artifacts/governance/decision-log.md`

## Models & Tools

**Tools:** bash, pytest, ruff, pip

**Models:** (to be filled by defaults)

## Repository

**Branch:** `feat/job-entrypoints-refactor`

**Merge Strategy:** squash

---

## Technical Notes

### API Design Principles

**Pure Function Approach:**
```python
# Canonizer's responsibility: raw_json + transform_id → canonical_json
canonical = canonicalize(raw_document, transform_id="email/gmail_to_jmap_lite@1.0.0")
```

**Orchestration happens outside:**
```python
# lorchestra job (NOT in canonizer)
from canonizer import canonicalize
from lorchestra.stack_clients.event_client import emit_event

def canonicalize_emails_from_bq():
    rows = bq_client.query("SELECT * FROM raw_events WHERE ...")

    for row in rows:
        canonical = canonicalize(row.payload, transform_id="...")
        emit_event("email.canonicalized", payload=canonical)
```

### Transform ID Resolution

The `transform_id` parameter accepts two formats:

1. **Registry-style ID** (recommended):
   - `"email/gmail_to_jmap_lite@1.0.0"`
   - Canonizer resolves to local transform path

2. **Full path to .meta.yaml** (legacy):
   - `"transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"`
   - Direct file path

### Error Handling

Functions raise exceptions for failures:

```python
from canonizer import canonicalize
from canonizer.core.validator import ValidationError

try:
    canonical = canonicalize(raw_doc, transform_id="email/gmail_to_jmap_lite@1.0.0")
except ValidationError as e:
    print(f"Validation failed: {e.errors}")
except Exception as e:
    print(f"Transform failed: {e}")
```

Batch processing collects errors:

```python
from canonizer import run_batch

results = []
errors = []

for doc in documents:
    try:
        canonical = canonicalize(doc, transform_id=transform_id)
        results.append(canonical)
    except Exception as e:
        errors.append({"doc": doc, "error": str(e)})
```

### CLI Backward Compatibility

The CLI becomes a thin wrapper:

```python
# canonizer/cli/cmds/transform.py (simplified)

import json
from pathlib import Path
from canonizer import canonicalize

def run(meta: Path, input: Path, output: Path):
    # 1. Read JSON
    input_data = json.loads(input.read_text())

    # 2. Transform (pure function call)
    canonical = canonicalize(input_data, transform_id=infer_from_meta(meta))

    # 3. Write JSON
    output.write_text(json.dumps(canonical, indent=2))
```

---

## Migration Path for Users

### Before (v0.3.0)

```bash
# CLI only
can transform run \
  --meta transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml \
  --input email.json \
  --output canonical.json
```

### After (v0.4.0)

```python
# Programmatic API (primary)
from canonizer import canonicalize

canonical = canonicalize(
    raw_gmail_message,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)

# Or use convenience functions
from canonizer import canonicalize_email_from_gmail

canonical = canonicalize_email_from_gmail(raw_gmail_message, format="lite")
```

```bash
# CLI still works (backward compatible)
can transform run --meta ... --input ... --output ...
```

### For lorchestra Integration

```python
# In lorchestra job (separate package)
from canonizer import canonicalize
from lorchestra.stack_clients.event_client import emit_event

def canonicalize_email_job():
    # 1. Get raw events from BQ
    rows = bq_client.query("SELECT * FROM raw_events WHERE ...")

    # 2. Transform each
    for row in rows:
        canonical = canonicalize(row.payload, transform_id="email/gmail_to_jmap_lite@1.0.0")

        # 3. Emit canonical event
        emit_event("email.canonicalized", payload=canonical, metadata={...})
```

---

## Success Metrics

After completion, verify:

- [ ] All 94 existing tests pass (no regression)
- [ ] ≥5 new integration tests for API functions
- [ ] Test coverage maintained at ≥44% overall
- [ ] Core modules (runtime, validator, executor) at 90%+ coverage
- [ ] API module at ≥80% coverage
- [ ] CLI backward compatibility confirmed (existing commands work)
- [ ] Package installs with `pip install canonizer` (no CLI deps)
- [ ] Package installs with `pip install canonizer[cli]` (with CLI)
- [ ] Documentation complete (API.md, updated README with examples)
- [ ] CHANGELOG updated with v0.4.0 release notes
- [ ] `from canonizer import canonicalize` works and is well-documented
- [ ] NO event_client, bq_client, or orchestration logic in canonizer