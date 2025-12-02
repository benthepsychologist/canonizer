---
version: "0.1"
tier: B
title: Node Canonizer Core Refactor
owner: benthepsychologist
goal: Refactor canonizer to use Node.js as the primary JSONata+extensions runtime, with Python as a thin wrapper
labels: [refactor, node, jsonata, architecture, breaking]
project_slug: canonizer
spec_version: 0.1.0
created: 2025-12-02T00:00:00+00:00
updated: 2025-12-02T00:00:00+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/node-refactor"
---

# Node Canonizer Core Refactor

## Objective

> Refactor canonizer to use Node.js as the primary runtime for JSONata transforms with extension functions (html→md, etc.). Python remains the interface layer for injest/final-form consumers.

## Context

### Why Now?

1. **Pre-production window**: No production workloads depend on canonizer yet
2. **Small surface area**: Only ~6 working transforms, easy to migrate
3. **Just finalized schemas**: New 5-entity canonical model (contact, clinical_session, clinical_document, session_transcript, billing_event)
4. **Extension functions needed**: HTML→Markdown conversion requires JS helpers that don't exist in Python JSONata
5. **Python JSONata is second-rate**: The `jsonata-python` library lacks full parity with official Node implementation

### Current State

```
canonizer/
├── canonizer/              # Python package
│   ├── api.py              # Main API: validate_payload(), canonicalize()
│   ├── core/
│   │   ├── jsonata_exec.py # Subprocess calls to Node (brittle inline script)
│   │   ├── runtime.py      # TransformRuntime
│   │   └── validator.py    # JSON Schema validation
│   └── ...
├── schemas/                # JSON Schemas (source + canonical)
└── transforms/             # .jsonata files + meta.yaml
```

The current `jsonata_exec.py` already calls Node via subprocess, but:
- No extension function support
- Inline Node script generation (brittle)
- No proper Node package structure
- No dependency management

### Target State

```
canonizer/
├── packages/
│   └── canonizer-core/           # Node.js package (THE engine)
│       ├── package.json
│       ├── src/
│       │   ├── index.ts          # Main exports
│       │   ├── runtime.ts        # TransformRuntime
│       │   ├── loader.ts         # TransformSpec loader
│       │   ├── validator.ts      # JSON Schema validation (ajv)
│       │   ├── extensions/       # Extension functions
│       │   │   ├── index.ts
│       │   │   └── htmlToMarkdown.ts
│       │   └── cli.ts            # CLI entry point
│       └── bin/
│           └── canonizer-core    # CLI binary
├── python/
│   └── canonizer/                # Python package (THIN wrapper only)
│       ├── api.py                # Same public API, calls canonizer-core
│       └── ...
├── registry/                     # Schemas + transforms (renamed from schemas/ + transforms/)
│   ├── schemas/
│   └── transforms/
└── .specwright/
```

**Key structural decisions:**
- `packages/canonizer-core/` - Proto-monorepo structure for future tools
- `python/canonizer/` - Python is just a subprocess wrapper, no logic
- All validation moves to Node (ajv) - Python does not validate
- Local-only Node package (no npm publish until external consumers exist)

### Naming Conventions

**Transform IDs:**
- Format: `{domain}/{name}` (e.g., `clinical_document/dataverse_to_canonical`)
- Version: `1-0-0` (dash-separated, matching Iglu convention)
- CLI usage: `--transform {domain}/{name}@{version}`

**Schema URIs (Iglu format):**
- Format: `iglu:{vendor}/{name}/{format}/{version}`
- Example: `iglu:com.microsoft/dataverse_report/jsonschema/1-0-0`

### Registry Path Resolution

```
registryRoot/
├── schemas/
│   └── {vendor}/
│       └── {name}/
│           └── {format}/
│               └── {version}.json
└── transforms/
    └── {domain}/
        └── {name}/
            └── {version}/
                ├── spec.meta.yaml
                └── spec.jsonata
```

Examples:
- `iglu:com.microsoft/dataverse_report/jsonschema/1-0-0`
  → `{registryRoot}/schemas/com.microsoft/dataverse_report/jsonschema/1-0-0.json`
- `clinical_document/dataverse_to_canonical@1-0-0`
  → `{registryRoot}/transforms/clinical_document/dataverse_to_canonical/1-0-0/spec.meta.yaml`

### I/O Contract

- **stdout**: JSON result only (success case)
- **stderr**: Error messages (plain text)
- **exit code**: 0 = success, non-zero = failure

Python wrapper treats stderr as error message string. No structured error objects in v1.

## Architecture

### 1. Node canonizer-core Package

The Node package is the "real" canonizer engine - ALL logic lives here:

```typescript
// src/runtime.ts
import jsonata from 'jsonata';
import Ajv from 'ajv';
import { loadSchema } from './loader';
import { registerExtensions } from './extensions';

interface TransformSpec {
  id: string;
  version: string;
  sourceSchema: string;
  targetSchema: string;
  extensions: ExtensionRef[];  // e.g., [{ name: "htmlToMarkdown", impl: "1.0.0" }]
  body: string;
}

interface RunOptions {
  validateInput?: boolean;   // default: true
  validateOutput?: boolean;  // default: true
  registryRoot?: string;
}

export async function runTransform(
  transformId: string,
  input: unknown,
  options: RunOptions = {}
): Promise<unknown> {
  const { validateInput = true, validateOutput = true, registryRoot } = options;

  // Load transform spec
  const spec = loadTransformSpec(transformId, registryRoot);

  // Validate input against sourceSchema
  if (validateInput) {
    const sourceSchema = loadSchema(spec.sourceSchema, registryRoot);
    validateAgainstSchema(input, sourceSchema, 'input');
  }

  // Execute JSONata with extensions
  const expr = jsonata(spec.body);
  registerExtensions(expr, spec.extensions);
  const output = await expr.evaluate(input);

  // Validate output against targetSchema
  if (validateOutput) {
    const targetSchema = loadSchema(spec.targetSchema, registryRoot);
    validateAgainstSchema(output, targetSchema, 'output');
  }

  return output;
}
```

### 2. Extension Function Pattern

Extensions are pure, versioned helper functions:

```typescript
// src/extensions/htmlToMarkdown.ts
import TurndownService from 'turndown';

const turndown = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
});

export function htmlToMarkdown(html: string): string {
  if (!html) return '';
  return turndown.turndown(html);
}
```

Transform specs declare required extensions with explicit versioning:

```yaml
# transforms/clinical_document/dataverse_to_canonical/1-0-0/spec.meta.yaml
id: clinical_document/dataverse_to_canonical
version: 1-0-0
source_schema: iglu:com.microsoft/dataverse_report/jsonschema/1-0-0
target_schema: iglu:org.canonical/clinical_document/jsonschema/1-0-0
extensions:
  - name: htmlToMarkdown
    impl: canonizer.extensions.html_to_markdown@1.0.0
checksum: sha256:abc123...
```

**Extension versioning rule**: Extensions are versioned separately (code units), but any extension behavior change requires bumping the transform spec version (contract unit). The transform version is what consumers depend on.

### 3. CLI Interface

```bash
# Run transform via CLI (stdin/stdout)
cat input.json | canonizer-core run --transform clinical_document/dataverse_to_canonical@1.0.0 > output.json

# Or with file paths
canonizer-core run \
  --transform clinical_document/dataverse_to_canonical@1.0.0 \
  --input input.json \
  --output output.json

# Validate extension availability
canonizer-core check --transform clinical_document/dataverse_to_canonical@1.0.0
```

### 4. Python Wrapper (THIN - No Logic)

Python is **only** a subprocess bridge. No validation, no transform logic, no schema loading:

```python
# python/canonizer/api.py
import json
import shutil
import subprocess
from pathlib import Path


def canonicalize(
    raw_document: dict,
    *,
    transform_id: str,
    validate: bool = True,
) -> dict:
    """Transform raw JSON document to canonical format."""
    return _call_node('run', transform_id, raw_document, validate)


def validate_payload(
    payload: dict,
    schema_iglu: str,
) -> tuple[bool, list[str]]:
    """Validate payload against schema. Returns (is_valid, errors)."""
    result = subprocess.run(
        [_get_canonizer_core_bin(), 'validate', '--schema', schema_iglu],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, []
    else:
        # stderr contains error messages, one per line
        errors = [line for line in result.stderr.strip().split('\n') if line]
        return False, errors


def run_batch(
    documents: list[dict],
    *,
    transform_id: str,
    validate: bool = True,
) -> list[dict]:
    """Transform multiple documents. Just a loop over canonicalize()."""
    return [canonicalize(doc, transform_id=transform_id, validate=validate) for doc in documents]


def _call_node(cmd: str, transform_id: str, data: dict, validate: bool) -> dict:
    """Call canonizer-core subprocess."""
    args = [_get_canonizer_core_bin(), cmd, '--transform', transform_id]
    if not validate:
        args.append('--no-validate')

    result = subprocess.run(
        args,
        input=json.dumps(data),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise TransformError(result.stderr.strip())

    return json.loads(result.stdout)


def _get_canonizer_core_bin() -> str:
    """Resolve path to canonizer-core binary."""
    # 1. Check for repo-local dev path
    repo_bin = Path(__file__).parent.parent.parent / 'packages/canonizer-core/bin/canonizer-core'
    if repo_bin.exists():
        return str(repo_bin)

    # 2. Check PATH
    if shutil.which('canonizer-core'):
        return 'canonizer-core'

    raise RuntimeError(
        "canonizer-core not found. Either:\n"
        "  - Run 'npm install' in packages/canonizer-core/\n"
        "  - Or install canonizer-core globally"
    )
```

**Python does NOT**:
- Load schemas
- Validate JSON
- Parse YAML
- Execute JSONata
- Know about extensions

Python **only** does:
- JSON serialization/deserialization
- Subprocess management
- Error propagation

## Acceptance Criteria

### Phase 1: Node Core
- [x] `packages/canonizer-core/` Node package with TypeScript
- [x] TransformSpec loader (reads meta.yaml + .jsonata)
- [x] JSON Schema validation with ajv (input + output)
- [x] JSONata execution with extension function registration
- [x] `htmlToMarkdown` extension function (using turndown)
- [x] CLI: `canonizer-core run --transform <id> < input.json > output.json`
- [x] Unit tests for runtime, validation, and extensions

### Phase 2: Python Integration
- [x] Move Python package to `python/canonizer/`
- [x] Python wrapper calls `canonizer-core` CLI (subprocess only)
- [x] Remove ALL Python validation/transform logic
- [x] Same public API signatures: `canonicalize()`, `validate_payload()`, `run_batch()`
- [x] Integration tests passing
- [x] Remove Python JSONata dependency
- [x] Remove Python jsonschema dependency

### Phase 3: Transform Migration
- [x] Port all existing transforms to new structure
- [x] Add `extensions[]` to meta.yaml format
- [x] Update Dataverse transforms to use `htmlToMarkdown()`
- [x] All transform tests passing

### Phase 4: Cleanup
- [x] Remove old Python modules (`jsonata_exec.py`, `validator.py`, etc.)
- [x] Update documentation
- [ ] Update pyproject.toml dependencies
- [ ] CI/CD updates for Node build

## Scope

### In Scope

1. **Node canonizer-core package** (`packages/canonizer-core/`)
   - TypeScript implementation
   - JSONata runtime with extensions
   - JSON Schema validation (ajv)
   - CLI binary
   - `htmlToMarkdown` extension

2. **Python wrapper refactor** (`python/canonizer/`)
   - Move to new location
   - Replace ALL logic with subprocess calls
   - Keep public API signatures identical
   - Remove jsonata-python and jsonschema dependencies

3. **Repo structure refactor**
   - `packages/` directory for Node
   - `python/` directory for Python wrapper
   - Keep `schemas/` and `transforms/` at root (or move to `registry/`)

4. **Transform spec updates**
   - Add `extensions[]` field to meta.yaml
   - Update existing transforms

### Out of Scope (Deferred)

- Additional extension functions beyond `htmlToMarkdown`
- Remote registry (separate spec)
- Stripe transforms (resume dataverse-and-stripe-schemas spec after this)
- npm publishing (local-only for now)
- Breaking Python API changes (signatures stay same)

## Plan

### Step 1: Initialize Node Package [G0: Plan Approval]

**Prompt:**

Create the `packages/canonizer-core/` Node.js package with TypeScript configuration.

**Outputs:**
- `packages/canonizer-core/package.json`
- `packages/canonizer-core/tsconfig.json`
- `packages/canonizer-core/.gitignore`
- `packages/canonizer-core/src/index.ts` (placeholder)

---

### Step 2: Implement TransformSpec Loader [G1: Code Readiness]

**Prompt:**

Implement the TransformSpec loader that reads meta.yaml and .jsonata files.

```typescript
interface ExtensionRef {
  name: string;
  impl: string;  // e.g., "canonizer.extensions.html_to_markdown@1.0.0"
}

interface TransformSpec {
  id: string;
  version: string;
  sourceSchema: string;
  targetSchema: string;
  extensions: ExtensionRef[];
  body: string;
  checksum?: string;
}

function loadTransformSpec(transformId: string, registryRoot: string): TransformSpec
function loadSchema(schemaUri: string, registryRoot: string): object
```

**Outputs:**
- `packages/canonizer-core/src/loader.ts`
- `packages/canonizer-core/src/types.ts`
- `packages/canonizer-core/tests/loader.test.ts`

---

### Step 3: Implement JSON Schema Validation [G1: Code Readiness]

**Prompt:**

Implement JSON Schema validation using ajv. This is the ONLY place validation happens - not Python.

```typescript
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

function validateAgainstSchema(
  data: unknown,
  schema: object,
  context: 'input' | 'output'
): void  // throws ValidationError
```

**Outputs:**
- `packages/canonizer-core/src/validator.ts`
- `packages/canonizer-core/tests/validator.test.ts`

---

### Step 4: Implement Extension Registry [G1: Code Readiness]

**Prompt:**

Implement the extension function registry and `htmlToMarkdown` extension.

```typescript
// Extension registry - versioned implementations
const extensions: Record<string, Function> = {
  'canonizer.extensions.html_to_markdown@1.0.0': htmlToMarkdownV1,
};

function registerExtensions(expr: jsonata.Expression, extensionRefs: ExtensionRef[]): void
```

**Outputs:**
- `packages/canonizer-core/src/extensions/index.ts`
- `packages/canonizer-core/src/extensions/htmlToMarkdown.ts`
- `packages/canonizer-core/tests/extensions.test.ts`

---

### Step 5: Implement Runtime [G1: Code Readiness]

**Prompt:**

Implement the transform runtime that ties together loader, validation, extensions, and JSONata.

```typescript
interface RunOptions {
  validateInput?: boolean;   // default: true
  validateOutput?: boolean;  // default: true
  registryRoot?: string;
}

async function runTransform(
  transformId: string,
  input: unknown,
  options?: RunOptions
): Promise<unknown>
```

**Outputs:**
- `packages/canonizer-core/src/runtime.ts`
- `packages/canonizer-core/tests/runtime.test.ts`

---

### Step 6: Implement CLI [G1: Code Readiness]

**Prompt:**

Implement CLI with three commands:

```bash
# Transform stdin to stdout
canonizer-core run --transform <id>@<version> [--registry path] [--no-validate]

# Validate stdin against schema (no transform)
canonizer-core validate --schema <iglu-uri> [--registry path]

# Version info
canonizer-core version
```

I/O contract:
- Input: JSON from stdin
- Output: JSON to stdout (success) or error message to stderr (failure)
- Exit code: 0 = success, non-zero = failure

For `validate`:
- Exit 0 + empty stdout = valid
- Exit non-zero + error lines on stderr = invalid

**Outputs:**
- `packages/canonizer-core/src/cli.ts`
- `packages/canonizer-core/bin/canonizer-core`
- `packages/canonizer-core/tests/cli.test.ts`

---

### Step 7: Refactor Python Package Structure [G2: Pre-Release]

**Prompt:**

Move Python package to `python/canonizer/` and strip ALL logic. Python becomes a pure subprocess wrapper.

```python
# python/canonizer/api.py
# ONLY: json.dumps, subprocess.run, json.loads, raise errors
# NO: schema loading, validation, yaml parsing, jsonata
```

Remove these Python modules entirely:
- `canonizer/core/validator.py`
- `canonizer/core/jsonata_exec.py`
- `canonizer/core/runtime.py`

Keep only:
- `python/canonizer/api.py` (thin wrapper)
- `python/canonizer/cli/` (if still needed for Python CLI)

**Outputs:**
- `python/canonizer/api.py` (rewritten as thin wrapper)
- Updated `python/pyproject.toml`
- Remove old Python modules
- `python/tests/integration/test_node_bridge.py`

---

### Step 8: Update Transform Meta Format [G2: Pre-Release]

**Prompt:**

Update spec.meta.yaml format to include `extensions[]` field with name+impl structure.
Update existing transforms.

**Outputs:**
- All existing `spec.meta.yaml` files updated with new format

---

### Step 9: Migrate Dataverse Transforms [G2: Pre-Release]

**Prompt:**

Create/update Dataverse transforms with `htmlToMarkdown` usage:
- contact (no HTML fields)
- clinical_session (no HTML fields)
- clinical_document (HTML→Markdown in content.text)
- session_transcript (HTML→Markdown in content.text)

**Outputs:**
- Updated transform files
- Transform test fixtures

---

### Step 10: Cleanup and Documentation [G3: Release Ready]

**Prompt:**

Final cleanup, update documentation, CI/CD.

**Outputs:**
- Update root `README.md`
- Update `python/pyproject.toml` (remove jsonata-python, jsonschema)
- Update CI workflow for Node build + Python tests
- Add Node prerequisite documentation

## Dependencies

### Node Dependencies (packages/canonizer-core/package.json)

```json
{
  "name": "canonizer-core",
  "version": "0.1.0",
  "type": "module",
  "bin": {
    "canonizer-core": "./bin/canonizer-core"
  },
  "dependencies": {
    "jsonata": "^2.0.0",
    "turndown": "^7.1.0",
    "yaml": "^2.3.0",
    "commander": "^12.0.0",
    "ajv": "^8.12.0",
    "ajv-formats": "^2.1.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/turndown": "^5.0.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "tsx": "^4.0.0"
  }
}
```

### Python Dependencies (python/pyproject.toml)

```toml
# REMOVE these - no longer needed
# jsonata-python
# jsonschema

# KEEP only
# pydantic (for error types maybe)
# No validation deps - Node does all validation
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Node not installed on target systems | High | Document requirement, add check in Python wrapper |
| JSONata version mismatch | Medium | Pin JSONata version, test parity |
| Extension function bugs | Medium | Unit tests, integration tests |
| Performance regression (subprocess overhead) | Low | Batch mode, connection pooling future |

## Resolved Decisions

These questions were reviewed and answered:

1. **Node package location**: `packages/canonizer-core/`
   - Proto-monorepo structure for future tools
   - Keeps repo organized as it grows

2. **Extension versioning**: Yes, extensions are versioned separately
   - Extensions are code units (e.g., `canonizer.extensions.html_to_markdown@1.0.0`)
   - Transforms are contract units - must bump version if extension behavior changes
   - Transform specs declare extensions with `name` + `impl` fields

3. **Validation in Node**: YES - all validation moves to Node
   - Python wrapper does NO validation
   - Node uses ajv for JSON Schema validation
   - "Thin wrapper means thin wrapper means thin wrapper"

4. **npm publishing**: No for now
   - Local-only package
   - Revisit only when external consumers exist
   - Version is internal detail controlled by repo

## Notes

- This spec supersedes transform-related work in `dataverse-and-stripe-schemas` spec
- The 5 canonical schemas created in that spec remain valid
- Dataverse/Stripe transforms will be created using the new Node runtime
- Python consumers (injest, final-form, lorchestra) continue to use `from canonizer import canonicalize`
