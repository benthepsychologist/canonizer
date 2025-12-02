---
version: "0.1"
tier: C
title: Dataverse and Stripe Schemas
owner: benthepsychologist
goal: Add source schemas, canonical schemas, and transforms for Dataverse and Stripe data sources
labels: [schemas, transforms, dataverse, stripe]
project_slug: canonizer
spec_version: 1.0.0
created: 2025-12-02T11:55:47.073839+00:00
updated: 2025-12-02T11:55:47.073839+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/dataverse-and-stripe-schemas"
---

# Dataverse and Stripe Schemas

## Objective

> Add source schemas, canonical schemas, and versioned transforms for Dataverse (contacts, sessions, reports) and Stripe (customers, invoices, payment_intents, refunds) data sources. Canonical schemas are OURS - designed for fields we depend on, guided by relevant standards.

## Acceptance Criteria

- [ ] Dataverse source schemas created (contact, session, report)
- [ ] Dataverse canonical schemas created (contact, clinical_session, clinical_report)
- [ ] Dataverse transforms versioned with tests
- [ ] Stripe source schemas created (customer, invoice, payment_intent, refund)
- [ ] Stripe canonical schemas created (customer, invoice, payment, refund)
- [ ] Stripe transforms created with tests
- [ ] All transforms pass validation
- [ ] CI green (lint + unit)

## Context

### Background

The canonizer library is a pure JSON transformation engine. We have working transforms for:
- Gmail → JMAP email (full, lite, minimal)
- Exchange → JMAP email (full, lite, minimal)
- Google Forms → canonical form_response

We need to add support for:
- **Dataverse**: CRM data from Microsoft Dynamics (contacts, clinical sessions, reports)
- **Stripe**: Billing data (customers, invoices, payments, refunds)

Bare `.jsonata` files exist for Dataverse but need proper versioning.
Nothing exists for Stripe yet.

### Canonical Schema Philosophy

Canonical schemas are **OURS** - they define the fields we depend on for downstream processing.
However, we align with standards where sensible:
- **Clinical data**: FHIR R4 (Patient, Encounter, DocumentReference)
- **Financial data**: ISO 20022, OpenFinance patterns

### Transform Structure

Each versioned transform needs:
```
transforms/<category>/<transform_name>/1.0.0/
├── spec.jsonata          # Transform logic
├── spec.meta.yaml        # Metadata (schemas, checksums)
└── tests/
    ├── input.json        # Sample input
    └── expected.json     # Expected output
```

### Constraints

- Transforms must be pure functions (no I/O)
- All transforms need input/output schema validation
- Checksums required in meta.yaml
- Tests required for each transform

## Plan

### Phase 1: Dataverse Schemas and Transforms

### Step 1: Research FHIR Standards [G0: Plan Approval]

**Prompt:**

Research FHIR R4 resources relevant to our Dataverse entities:
- FHIR Patient → contact
- FHIR Encounter → clinical_session
- FHIR DocumentReference → clinical_report

Document which FHIR fields map to our needs and which we'll simplify.
We're not implementing full FHIR - just borrowing sensible field names and structures.

**Outputs:**

- `artifacts/phase1/fhir-mapping-research.md`

### Step 2: Create Dataverse Source Schemas

**Prompt:**

Create source schemas based on actual Dataverse API response structures.
Look at sample ingested data from lorchestra's raw_objects table or Dataverse API docs.

Create:
- `schemas/com.microsoft/dataverse_contact/jsonschema/1-0-0.json`
- `schemas/com.microsoft/dataverse_session/jsonschema/1-0-0.json`
- `schemas/com.microsoft/dataverse_report/jsonschema/1-0-0.json`

**Outputs:**

- `schemas/com.microsoft/dataverse_contact/jsonschema/1-0-0.json`
- `schemas/com.microsoft/dataverse_session/jsonschema/1-0-0.json`
- `schemas/com.microsoft/dataverse_report/jsonschema/1-0-0.json`

### Step 3: Create Dataverse Canonical Schemas

**Prompt:**

Create canonical output schemas. Use FHIR-inspired field names where sensible.
These define the fields OUR downstream systems depend on.

Create:
- `schemas/org.canonical/contact/jsonschema/1-0-0.json`
- `schemas/org.canonical/clinical_session/jsonschema/1-0-0.json`
- `schemas/org.canonical/clinical_report/jsonschema/1-0-0.json`

**Outputs:**

- `schemas/org.canonical/contact/jsonschema/1-0-0.json`
- `schemas/org.canonical/clinical_session/jsonschema/1-0-0.json`
- `schemas/org.canonical/clinical_report/jsonschema/1-0-0.json`

### Step 4: Version Contact Transform

**Prompt:**

Convert existing `transforms/contact/dataverse_contact_to_canonical_v1.jsonata` to proper versioned structure.

Create:
- `transforms/contact/dataverse_to_canonical/1.0.0/spec.jsonata`
- `transforms/contact/dataverse_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/contact/dataverse_to_canonical/1.0.0/tests/input.json`
- `transforms/contact/dataverse_to_canonical/1.0.0/tests/expected.json`

Calculate SHA256 checksum for spec.jsonata and include in meta.yaml.

**Commands:**

```bash
sha256sum transforms/contact/dataverse_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/contact/dataverse_to_canonical/1.0.0/spec.jsonata`
- `transforms/contact/dataverse_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/contact/dataverse_to_canonical/1.0.0/tests/input.json`
- `transforms/contact/dataverse_to_canonical/1.0.0/tests/expected.json`

### Step 5: Version Clinical Session Transform

**Prompt:**

Convert existing `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata` to proper versioned structure.

**Commands:**

```bash
sha256sum transforms/clinical_session/dataverse_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/clinical_session/dataverse_to_canonical/1.0.0/spec.jsonata`
- `transforms/clinical_session/dataverse_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/clinical_session/dataverse_to_canonical/1.0.0/tests/input.json`
- `transforms/clinical_session/dataverse_to_canonical/1.0.0/tests/expected.json`

### Step 6: Version Report Transform

**Prompt:**

Convert existing `transforms/report/dataverse_report_to_canonical_v1.jsonata` to proper versioned structure.

**Commands:**

```bash
sha256sum transforms/report/dataverse_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/report/dataverse_to_canonical/1.0.0/spec.jsonata`
- `transforms/report/dataverse_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/report/dataverse_to_canonical/1.0.0/tests/input.json`
- `transforms/report/dataverse_to_canonical/1.0.0/tests/expected.json`

### Step 7: Test Dataverse Transforms

**Prompt:**

Run transform validation and tests for all Dataverse transforms.

**Commands:**

```bash
can transform run --meta transforms/contact/dataverse_to_canonical/1.0.0/spec.meta.yaml --input transforms/contact/dataverse_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
can transform run --meta transforms/clinical_session/dataverse_to_canonical/1.0.0/spec.meta.yaml --input transforms/clinical_session/dataverse_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
can transform run --meta transforms/report/dataverse_to_canonical/1.0.0/spec.meta.yaml --input transforms/report/dataverse_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
```

**Outputs:**

- `artifacts/phase1/dataverse-transform-tests.md`

---

### Phase 2: Stripe Schemas and Transforms

### Step 8: Research Financial Standards

**Prompt:**

Research standards for financial/billing data:
- ISO 20022 payment concepts
- OpenFinance/Open Banking patterns
- Common invoice schema patterns

Document which concepts apply to our Stripe data and which fields we need.

**Outputs:**

- `artifacts/phase2/financial-standards-research.md`

### Step 9: Create Stripe Source Schemas

**Prompt:**

Create source schemas based on Stripe API response structures.
Reference: https://stripe.com/docs/api

Create:
- `schemas/com.stripe/customer/jsonschema/1-0-0.json`
- `schemas/com.stripe/invoice/jsonschema/1-0-0.json`
- `schemas/com.stripe/payment_intent/jsonschema/1-0-0.json`
- `schemas/com.stripe/refund/jsonschema/1-0-0.json`

**Outputs:**

- `schemas/com.stripe/customer/jsonschema/1-0-0.json`
- `schemas/com.stripe/invoice/jsonschema/1-0-0.json`
- `schemas/com.stripe/payment_intent/jsonschema/1-0-0.json`
- `schemas/com.stripe/refund/jsonschema/1-0-0.json`

### Step 10: Create Stripe Canonical Schemas

**Prompt:**

Create canonical output schemas for billing data.
These define the fields OUR downstream systems depend on.

Create:
- `schemas/org.canonical/customer/jsonschema/1-0-0.json`
- `schemas/org.canonical/invoice/jsonschema/1-0-0.json`
- `schemas/org.canonical/payment/jsonschema/1-0-0.json`
- `schemas/org.canonical/refund/jsonschema/1-0-0.json`

**Outputs:**

- `schemas/org.canonical/customer/jsonschema/1-0-0.json`
- `schemas/org.canonical/invoice/jsonschema/1-0-0.json`
- `schemas/org.canonical/payment/jsonschema/1-0-0.json`
- `schemas/org.canonical/refund/jsonschema/1-0-0.json`

### Step 11: Create Customer Transform

**Prompt:**

Create Stripe customer to canonical customer transform.

**Commands:**

```bash
sha256sum transforms/customer/stripe_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/customer/stripe_to_canonical/1.0.0/spec.jsonata`
- `transforms/customer/stripe_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/customer/stripe_to_canonical/1.0.0/tests/input.json`
- `transforms/customer/stripe_to_canonical/1.0.0/tests/expected.json`

### Step 12: Create Invoice Transform

**Prompt:**

Create Stripe invoice to canonical invoice transform.

**Commands:**

```bash
sha256sum transforms/invoice/stripe_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/invoice/stripe_to_canonical/1.0.0/spec.jsonata`
- `transforms/invoice/stripe_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/invoice/stripe_to_canonical/1.0.0/tests/input.json`
- `transforms/invoice/stripe_to_canonical/1.0.0/tests/expected.json`

### Step 13: Create Payment Transform

**Prompt:**

Create Stripe payment_intent to canonical payment transform.

**Commands:**

```bash
sha256sum transforms/payment/stripe_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/payment/stripe_to_canonical/1.0.0/spec.jsonata`
- `transforms/payment/stripe_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/payment/stripe_to_canonical/1.0.0/tests/input.json`
- `transforms/payment/stripe_to_canonical/1.0.0/tests/expected.json`

### Step 14: Create Refund Transform

**Prompt:**

Create Stripe refund to canonical refund transform.

**Commands:**

```bash
sha256sum transforms/refund/stripe_to_canonical/1.0.0/spec.jsonata
```

**Outputs:**

- `transforms/refund/stripe_to_canonical/1.0.0/spec.jsonata`
- `transforms/refund/stripe_to_canonical/1.0.0/spec.meta.yaml`
- `transforms/refund/stripe_to_canonical/1.0.0/tests/input.json`
- `transforms/refund/stripe_to_canonical/1.0.0/tests/expected.json`

### Step 15: Test Stripe Transforms

**Prompt:**

Run transform validation and tests for all Stripe transforms.

**Commands:**

```bash
can transform run --meta transforms/customer/stripe_to_canonical/1.0.0/spec.meta.yaml --input transforms/customer/stripe_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
can transform run --meta transforms/invoice/stripe_to_canonical/1.0.0/spec.meta.yaml --input transforms/invoice/stripe_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
can transform run --meta transforms/payment/stripe_to_canonical/1.0.0/spec.meta.yaml --input transforms/payment/stripe_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
can transform run --meta transforms/refund/stripe_to_canonical/1.0.0/spec.meta.yaml --input transforms/refund/stripe_to_canonical/1.0.0/tests/input.json --validate-input --validate-output
```

**Outputs:**

- `artifacts/phase2/stripe-transform-tests.md`

---

### Phase 3: Validation and Cleanup

### Step 16: Run Full Test Suite [G1: Code Readiness]

**Prompt:**

Run the complete test suite to verify all transforms work correctly.

**Commands:**

```bash
pytest -q --tb=short
ruff check .
```

**Outputs:**

- `artifacts/phase3/test-results.md`

### Step 17: Clean Up Old Files

**Prompt:**

Remove the old unversioned .jsonata files that have been replaced:
- `transforms/contact/dataverse_contact_to_canonical_v1.jsonata`
- `transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata`
- `transforms/report/dataverse_report_to_canonical_v1.jsonata`

**Commands:**

```bash
git rm transforms/contact/dataverse_contact_to_canonical_v1.jsonata
git rm transforms/clinical_session/dataverse_session_to_canonical_v1.jsonata
git rm transforms/report/dataverse_report_to_canonical_v1.jsonata
```

**Outputs:**

- `artifacts/phase3/cleanup-complete.md`

### Step 18: Final Validation [G2: Pre-Release]

**Prompt:**

Final validation and documentation.

**Commands:**

```bash
pytest -v
can registry list --dir transforms/
```

**Outputs:**

- `artifacts/phase3/final-validation.md`

## Models & Tools

**Tools:** can CLI, pytest, ruff, sha256sum

**Models:** Claude (implementation), JSONata (transforms)

## Repository

**Branch:** `feat/dataverse-and-stripe-schemas`

**Merge Strategy:** squash
