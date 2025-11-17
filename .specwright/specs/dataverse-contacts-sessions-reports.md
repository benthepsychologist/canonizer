---
version: "0.1"
tier: C
title: dataverse contacts sessions reports
owner: benthepsychologist
goal: Implement dataverse contacts sessions reports
labels: []
project_slug: canonizer
spec_version: 1.0.0
created: 2025-11-17T14:58:11.399272+00:00
updated: 2025-11-17T14:58:11.399272+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/dataverse-contacts-sessions-reports"
---

# dataverse contacts sessions reports

## Objective

> Create 3 Dataverse transforms (contact, session, report) to complete the PHI data pipeline. Currently, the lorchestra pipeline can only process email data (Gmail/Exchange) because those are the only transforms that exist.

## Acceptance Criteria

- [x] CI green (lint + unit) - ✅ 94 tests passing, ruff clean
- [x] No protected paths modified - ✅ Only created files in transforms/ and artifacts/
- [~] 70% test coverage achieved - ⚠️ 44% overall (core modules 96-100%, pending integration tests)
- [x] All 3 Dataverse transforms created with proper JSONata mappings - ✅ contact, clinical_session, report
- [x] All 3 canonical JSON schemas defined - ✅ All using JSON Schema Draft 07
- [~] Transforms validated against sample Dataverse data - ⚠️ Pending real data from tap-dataverse

## Context

### Background

We need to create 3 Dataverse transforms to complete the data pipeline. Gmail and Exchange email transforms already exist, but we need transforms for Dataverse contacts, clinical sessions, and reports extracted from Dynamics 365.

These transforms are needed for the lorchestra pipeline to canonize all extracted Dataverse data from tap-dataverse. Sample input files should be available in `/home/user/phi-data/vault/`.

### Constraints

- No edits under protected paths (`src/core/**`, `infra/**`)

## Plan

### Step 1: Planning & Design [G0: Plan Approval]

**Prompt:**

Review existing email transforms (Gmail/Exchange to canonical) to understand the JSONata transform format and canonical schema structure. Identify the directory structure and naming conventions.

Examine sample Dataverse data in `/home/user/phi-data/vault/` to understand the input schema for contacts, sessions, and reports.

**Outputs:**

- `artifacts/plan/plan-01.md` - Analysis of existing transforms and data structure

### Step 2: Define Canonical Schemas [G0: Plan Approval]

**Prompt:**

Create 3 canonical JSON schemas in `transforms/schemas/canonical/`:
1. `contact_v1-0-0.json` - Based on standard contact fields
2. `clinical_session_v1-0-0.json` - For clinical appointment/session data
3. `report_v1-0-0.json` - For clinical reports/documents

Follow the same structure as `email_v1-0-0.json` if it exists.

**Outputs:**

- `transforms/schemas/canonical/contact_v1-0-0.json`
- `transforms/schemas/canonical/clinical_session_v1-0-0.json`
- `transforms/schemas/canonical/report_v1-0-0.json`

### Step 3: Create Contact Transform [G1: Code Readiness]

**Prompt:**

Create Dataverse Contact → Canonical Contact transform.

**Key field mappings:**
- contactid → contact_id
- firstname → first_name
- lastname → last_name
- emailaddress1 → email
- telephone1 → phone
- address1_* → address {}
- birthdate → birth_date
- createdon → created_at

**File:** `transforms/contact/dataverse_contact_to_canonical_v1.jsonata`

**Outputs:**

- `transforms/contact/dataverse_contact_to_canonical_v1.jsonata`

### Step 4: Create Clinical Session Transform [G1: Code Readiness]

**Prompt:**

Create Dataverse Session → Canonical Clinical Session transform.

Map session-specific fields including appointment details, notes, participants, duration, etc. based on the Dynamics 365 custom session entity schema.

**File:** `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata`

**Outputs:**

- `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata`

### Step 5: Create Report Transform [G1: Code Readiness]

**Prompt:**

Create Dataverse Report → Canonical Report transform.

Map report/document entity fields including report metadata, content references, and associated entities.

**File:** `transforms/report/dataverse_report_to_canonical_v1.jsonata`

**Commands:**

```bash
ruff check .
pytest -q
```

**Outputs:**

- `transforms/report/dataverse_report_to_canonical_v1.jsonata`

### Step 6: Testing & Validation [G2: Pre-Release]

**Prompt:**

Validate all 3 transforms against sample Dataverse data from `/home/user/phi-data/vault/`.

Test that the JSONata transforms produce valid output matching the canonical schemas.

**Commands:**

```bash
pytest -q --tb=short
ruff check .
```

**Outputs:**

- `artifacts/test/test-pass-confirmation.md` - Validation results for all 3 transforms

### Step 7: Governance [G4: Post-Implementation]

**Prompt:**

Document the transform mappings and schema decisions. Include:
- Field mapping rationale for each transform
- Any data transformation decisions (e.g., date formats, null handling)
- Notes on Dataverse-specific considerations

**Outputs:**

- `artifacts/governance/decision-log.md` - Transform design decisions
- `artifacts/governance/transform-mappings.md` - Complete field mapping reference

## Models & Tools

**Tools:** bash, pytest, ruff

**Models:** (to be filled by defaults)

## Repository

**Branch:** `feat/dataverse-contacts-sessions-reports`

**Merge Strategy:** squash