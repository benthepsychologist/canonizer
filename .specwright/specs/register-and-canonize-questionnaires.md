---
version: "0.1"
tier: C
title: Add Form Response Schemas and Google Forms Transform
owner: benthepsychologist
goal: Implement Layer 1 platform normalization for form responses
labels: [schemas, transforms, forms]
project_slug: canonizer
spec_version: 1.0.0
created: 2025-11-13T20:35:57.903545+00:00
updated: 2025-11-17T14:30:00.000000+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "main"
---

# Add Form Response Schemas and Google Forms Transform

## Objective

> Implement Layer 1 schema normalization for Google Forms responses. Create canonical form_response schema and transform Google Forms API format to canonical format.

## Acceptance Criteria

- [x] Google Forms source schema created (com.google/forms_response)
- [x] Canonical form_response schema created (org.canonical/form_response)
- [x] Google Forms to canonical transform created with JSONata
- [x] Golden tests pass for transform
- [x] All artifacts added to canonizer-registry
- [x] Registry validation passes
- [x] Transform discoverable via `can registry` CLI

## Context

### Background

The canonizer tool separates data transformation into two layers:
- **Layer 1 (Canonizer)**: Platform normalization - converting platform-specific API formats to canonical schemas
- **Layer 2 (Separate tool)**: Domain processing - extracting domain entities (questionnaires, etc.) from canonical data

This work implements Layer 1 for Google Forms, enabling consistent form response processing regardless of platform (Google Forms, Typeform, Microsoft Forms, etc.).

### Constraints

- Must follow canonizer-registry structure and validation rules
- Must use JSONata for transforms (no code execution)
- Golden tests required for all transforms

## Plan

### Step 1: Schema Design

**Task:** Design and create JSON schemas for Google Forms API format and canonical form_response.

**Deliverables:**
- `schemas/com.google/forms_response/jsonschema/1-0-0.json` - Google Forms API v1 FormResponse
- `schemas/org.canonical/form_response/jsonschema/1-0-0.json` - Platform-agnostic form submission
- Documentation of two-layer architecture in `docs/QUESTIONNAIRE_CANONICALIZATION.md`

**Status:** ✅ Complete

### Step 2: JSONata Transform Creation

**Task:** Implement JSONata transform to convert Google Forms API format to canonical form_response.

**Deliverables:**
- `transforms/forms/google_forms_to_canonical/1.0.0/spec.jsonata` - Transform logic
- `transforms/forms/google_forms_to_canonical/1.0.0/spec.meta.yaml` - Metadata with checksum
- `transforms/forms/google_forms_to_canonical/1.0.0/tests/input.json` - Golden test input
- `transforms/forms/google_forms_to_canonical/1.0.0/tests/expected.json` - Golden test expected output

**Key Implementation Details:**
- Flattens nested `textAnswers.answers[0].value` structure
- Converts `answers` object to flat array with `question_id`, `answer_value`, `answer_type`
- Extracts respondent metadata and timestamps
- Wraps JSONata in parentheses for proper object literal evaluation

**Status:** ✅ Complete

### Step 3: Local Validation

**Task:** Validate transform locally with golden tests.

**Commands:**
```bash
can validate run --transform transforms/forms/google_forms_to_canonical/1.0.0/
```

**Status:** ✅ Complete - Transform output matches expected exactly

### Step 4: Registry Integration

**Task:** Add schemas and transform to canonizer-registry.

**Deliverables:**
- Copy schemas to `/canonizer-registry/schemas/`
- Copy transform to `/canonizer-registry/transforms/`
- Compute SHA256 checksum for spec.jsonata
- Run registry validation: `python tools/validate.py`

**Commands:**
```bash
cd /home/user/canonizer-registry
python tools/validate.py --repo-root .
```

**Status:** ✅ Complete - All 8 schemas and 8 transforms validated

### Step 5: Registry Publication

**Task:** Commit and push to canonizer-registry, trigger CI.

**Deliverables:**
- Git commit with schemas and transform
- CI runs validation and generates updated `REGISTRY_INDEX.json`
- Transform becomes discoverable via `can registry list`

**Status:** ✅ Complete - Transform available at `forms/google_forms_to_canonical@1.0.0`

## Implementation Summary

**Files Created in canonizer repo:**
- `schemas/com.google/forms_response/jsonschema/1-0-0.json` (184 lines)
- `schemas/org.canonical/form_response/jsonschema/1-0-0.json` (187 lines)
- `transforms/forms/google_forms_to_canonical/1.0.0/spec.jsonata` (27 lines)
- `transforms/forms/google_forms_to_canonical/1.0.0/spec.meta.yaml` (29 lines)
- `transforms/forms/google_forms_to_canonical/1.0.0/tests/input.json` (60 lines)
- `transforms/forms/google_forms_to_canonical/1.0.0/tests/expected.json` (42 lines)

**Files Added to canonizer-registry:**
- Same 6 files copied to registry
- Checksum computed: `265c20befcce7895e83b00c72faf78cb912c2b4a256b6993d722bc65d8278204`

**Registry CI:**
- Run ID: 19432150939
- Status: ✅ Success
- Generated commit: `48d7cfc` (REGISTRY_INDEX.json update)

**Validation:**
```bash
can registry search --from iglu:com.google/forms_response/jsonschema/1-0-0
# Returns: forms/google_forms_to_canonical@1.0.0 (stable)
```

## Models & Tools

**Tools:** JSONata, can CLI, git, GitHub Actions

**Models:** Claude Sonnet 4.5

## Repository

**Main Branch:** `main` (direct commits, no feature branch needed)

**Registry Branch:** `main` in benthepsychologist/canonizer-registry

**Commits:**
- canonizer: `691169f` - "feat: Add Google Forms to canonical form_response transform"
- canonizer-registry: `34a4e92` → `48d7cfc` - "feat: Add form response schemas and Google Forms transform"