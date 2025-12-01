---
version: "0.1"
tier: C
title: Bulk Import Command
owner: benthepsychologist
goal: Add `canonizer import all` command to bulk import schemas and transforms from a local registry clone
labels: [registry, local, cli, import]
project_slug: canonizer
spec_version: 0.1.0
created: 2025-12-01T00:00:00+00:00
updated: 2025-12-01T00:00:00+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/bulk-import"
---

# Bulk Import Command

## Objective

> Add a `canonizer import all` command that bulk imports all (or filtered) schemas and transforms from a local registry clone into `.canonizer/`.

## Context

### Problem

Currently, importing from a local registry clone requires importing each transform individually:

```bash
canonizer import run --from /path/to/registry "email/gmail_to_jmap_lite@1.0.0"
canonizer import run --from /path/to/registry "email/gmail_to_jmap_full@1.0.0"
# ... repeat for each transform
```

This is tedious when you want to sync an entire registry or category.

### Solution

Add a bulk import command:

```bash
# Import everything
canonizer import all --from /path/to/registry

# Import by category
canonizer import all --from /path/to/registry --category email

# Import only schemas
canonizer import all --from /path/to/registry --schemas-only

# Import only transforms (and their referenced schemas)
canonizer import all --from /path/to/registry --transforms-only
```

## Acceptance Criteria

- [ ] `canonizer import all --from <path>` imports all transforms and schemas
- [ ] `--category <name>` filters transforms by category (e.g., `email`, `forms`)
- [ ] `--schemas-only` imports only schemas
- [ ] `--transforms-only` imports only transforms (with referenced schemas)
- [ ] Progress output shows what's being imported
- [ ] `lock.json` is updated with all imported items
- [ ] Existing items are skipped or updated (not duplicated)
- [ ] Unit tests cover the new command

## Plan

### Step 1: Add `import all` Command [G0: Plan Approval]

**Prompt:**

Add the `all` subcommand to `canonizer/cli/cmds/import_cmd.py`:

1. Walk the source registry's `schemas/` and `transforms/` directories
2. Build list of all schema refs and transform refs
3. Apply filters (`--category`, `--schemas-only`, `--transforms-only`)
4. Import each item using existing `import_schema()` and `import_transform()` functions
5. Show progress with rich console output
6. Save lock.json once at the end

**Commands:**
```bash
ruff check canonizer/cli/cmds/import_cmd.py
pytest tests/unit/test_import_cmd.py -v
```

**Outputs:**
- `canonizer/cli/cmds/import_cmd.py` (updated)
- `tests/unit/test_import_cmd.py` (new or updated)

---

### Step 2: Test and Validate [G1: Code Readiness]

**Prompt:**

Test the bulk import command against a mock registry structure:

1. Create a temp directory with sample schemas and transforms
2. Run `canonizer import all --from <temp>`
3. Verify all items appear in `.canonizer/registry/`
4. Verify `lock.json` contains all entries with correct hashes
5. Test filter flags (`--category`, `--schemas-only`, `--transforms-only`)

**Commands:**
```bash
pytest tests/unit/test_import_cmd.py -v
pytest tests/integration/test_bulk_import.py -v
```

**Outputs:**
- `tests/integration/test_bulk_import.py`

---

### Step 3: Documentation [G2: Pre-Release]

**Prompt:**

Update README and docs with bulk import examples.

**Outputs:**
- `README.md` (updated)

## Notes

- This builds on the existing `import_cmd.py` infrastructure
- Reuses `import_schema()` and `import_transform()` functions
- No network access needed - purely local file operations
