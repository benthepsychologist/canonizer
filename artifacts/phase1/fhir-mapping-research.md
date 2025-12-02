# FHIR R4 Mapping Research for Dataverse Entities

## Overview

This document outlines the FHIR R4 resources relevant to our Dataverse entities and documents which fields we'll adopt, adapt, or simplify for our canonical schemas.

**Philosophy**: We're not implementing full FHIR compliance. We're borrowing sensible field names and structures that align with healthcare standards while keeping our schemas practical for downstream processing.

---

## 1. Contact → FHIR Patient Mapping

### FHIR Patient Resource ([HL7 FHIR R4 Patient](https://hl7.org/fhir/R4/patient.html))

The Patient resource contains demographics and administrative information about an individual receiving care.

### FHIR Patient Key Fields

| FHIR Field | Type | Description |
|------------|------|-------------|
| `identifier` | Identifier[] | Patient identifiers (MRN, SSN, etc.) |
| `name` | HumanName[] | Names associated with the patient |
| `telecom` | ContactPoint[] | Contact details (phone, email) |
| `gender` | code | male \| female \| other \| unknown |
| `birthDate` | date | Date of birth |
| `address` | Address[] | Addresses for the patient |
| `communication` | BackboneElement[] | Languages spoken |
| `generalPractitioner` | Reference[] | Patient's care providers |

### Our Canonical Contact Schema Decisions

| Our Field | FHIR Inspiration | Decision |
|-----------|------------------|----------|
| `id` | `identifier` | **Adopt** - Primary identifier |
| `name.given` | `name.given` | **Adopt** - FHIR naming convention |
| `name.family` | `name.family` | **Adopt** - FHIR naming convention |
| `telecom.email` | `telecom` (system=email) | **Simplify** - Flatten to direct fields |
| `telecom.phone` | `telecom` (system=phone) | **Simplify** - Flatten to direct fields |
| `telecom.mobile` | `telecom` (system=phone, use=mobile) | **Simplify** - Direct field |
| `birthDate` | `birthDate` | **Adopt** - Same field name |
| `address` | `address` | **Adapt** - Simplified structure |
| `meta.createdAt` | N/A | **Add** - Audit field |
| `meta.updatedAt` | N/A | **Add** - Audit field |
| `meta.source` | N/A | **Add** - Provenance tracking |

### Simplifications from Full FHIR

1. **Names**: FHIR supports multiple names with use codes (official, nickname, etc.). We'll use a single `name` object with `given` and `family`.
2. **Telecom**: FHIR uses a complex `ContactPoint` structure. We'll flatten to `telecom.email`, `telecom.phone`, `telecom.mobile`.
3. **Address**: FHIR supports multiple addresses with use codes. We'll support a single primary address with simplified structure.
4. **Identifiers**: FHIR supports multiple identifier systems. We'll use a single `id` field.

---

## 2. Clinical Session → FHIR Encounter Mapping

### FHIR Encounter Resource ([HL7 FHIR R4 Encounter](https://hl7.org/fhir/R4/encounter.html))

An Encounter is an interaction between a patient and healthcare provider(s) for providing healthcare services.

### FHIR Encounter Key Fields

| FHIR Field | Type | Description |
|------------|------|-------------|
| `identifier` | Identifier[] | Encounter identifiers |
| `status` | code | planned \| arrived \| triaged \| in-progress \| onleave \| finished \| cancelled |
| `class` | Coding | Classification (inpatient, outpatient, emergency, etc.) |
| `type` | CodeableConcept[] | Specific type of encounter |
| `subject` | Reference(Patient) | The patient present at the encounter |
| `period.start` | dateTime | Start time of encounter |
| `period.end` | dateTime | End time of encounter |
| `length` | Duration | Quantity of time the encounter lasted |
| `reasonCode` | CodeableConcept[] | Coded reason the encounter takes place |
| `participant` | BackboneElement[] | List of participants involved |

### Our Canonical Clinical Session Schema Decisions

| Our Field | FHIR Inspiration | Decision |
|-----------|------------------|----------|
| `id` | `identifier` | **Adopt** - Primary identifier |
| `status` | `status` | **Adapt** - Simplified status codes |
| `class` | `class` | **Adopt** - Session classification |
| `type` | `type` | **Simplify** - Single type string |
| `subject.reference` | `subject` | **Adopt** - Reference to contact |
| `period.start` | `period.start` | **Adopt** - Same structure |
| `period.end` | `period.end` | **Adopt** - Same structure |
| `period.scheduledStart` | N/A | **Add** - Scheduling distinction |
| `period.scheduledEnd` | N/A | **Add** - Scheduling distinction |
| `duration` | `length` | **Adapt** - Minutes as integer |
| `description` | `reasonCode.text` | **Simplify** - Free text description |
| `meta.createdAt` | N/A | **Add** - Audit field |
| `meta.updatedAt` | N/A | **Add** - Audit field |
| `meta.source` | N/A | **Add** - Provenance tracking |

### Status Code Mapping

| Dataverse Status | FHIR Status | Our Canonical Status |
|------------------|-------------|---------------------|
| 1 | planned | `scheduled` |
| 2 | finished | `completed` |
| 3 | cancelled | `cancelled` |
| 4 | in-progress | `in-progress` |
| 5 | N/A | `no-show` |

### Simplifications from Full FHIR

1. **Status**: FHIR has 9 status values. We'll use 5 practical values.
2. **Period**: We separate scheduled vs actual times (not in FHIR).
3. **Type**: FHIR uses CodeableConcept with coding systems. We'll use a simple string.
4. **Participants**: FHIR tracks all participants. We reference only the patient/contact.
5. **Class**: We'll use simple strings instead of Coding objects.

---

## 3. Clinical Report → FHIR DocumentReference Mapping

### FHIR DocumentReference Resource ([HL7 FHIR R4 DocumentReference](https://hl7.org/fhir/R4/documentreference.html))

A reference to a document providing metadata for discovery and management.

### FHIR DocumentReference Key Fields

| FHIR Field | Type | Description |
|------------|------|-------------|
| `identifier` | Identifier[] | Document identifiers |
| `status` | code | current \| superseded \| entered-in-error |
| `docStatus` | code | preliminary \| final \| amended \| entered-in-error |
| `type` | CodeableConcept | Kind of document (LOINC if possible) |
| `category` | CodeableConcept[] | Categorization of document |
| `subject` | Reference(Patient) | Who the document is about |
| `date` | instant | When document reference was created |
| `author` | Reference[] | Who authored the document |
| `description` | string | Human-readable description |
| `content` | BackboneElement[] | Document content (attachment + format) |
| `context.encounter` | Reference(Encounter)[] | Related encounters |

### Our Canonical Clinical Report Schema Decisions

| Our Field | FHIR Inspiration | Decision |
|-----------|------------------|----------|
| `id` | `identifier` | **Adopt** - Primary identifier |
| `status` | `docStatus` | **Adapt** - Document lifecycle status |
| `type` | `type` | **Simplify** - String type code |
| `title` | `description` | **Adopt** - Human-readable title |
| `subject.reference` | `subject` | **Adopt** - Reference to contact |
| `encounter.reference` | `context.encounter` | **Adopt** - Reference to session |
| `date` | `date` | **Adopt** - Report date |
| `content.text` | `content.attachment.data` | **Simplify** - Direct text content |
| `meta.createdAt` | N/A | **Add** - Audit field |
| `meta.updatedAt` | N/A | **Add** - Audit field |
| `meta.source` | N/A | **Add** - Provenance tracking |

### Document Status Mapping

| Dataverse Status | FHIR docStatus | Our Canonical Status |
|------------------|----------------|---------------------|
| 1 | preliminary | `draft` |
| 2 | final | `final` |
| 3 | amended | `amended` |
| 4 | N/A | `archived` |

### Simplifications from Full FHIR

1. **Status**: We use `docStatus` concept (document lifecycle) rather than `status` (reference lifecycle).
2. **Type/Category**: FHIR uses LOINC codes. We'll use simple string types.
3. **Content**: FHIR supports multiple content representations. We'll store primary text content directly.
4. **Author**: FHIR supports multiple authors. We omit this for simplicity (can be added later).
5. **Context**: We reference session directly instead of nested context object.

---

## Common Patterns Across All Schemas

### Meta Object (Our Addition)

All canonical schemas include a `meta` object for audit and provenance:

```json
{
  "meta": {
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-15T14:22:00Z",
    "source": {
      "system": "dataverse",
      "version": "1.0.0"
    }
  }
}
```

### Reference Pattern (FHIR-Inspired)

For relationships between entities, we use FHIR-style references:

```json
{
  "subject": {
    "reference": "contact/abc-123",
    "type": "Contact"
  }
}
```

### Naming Conventions

| Concept | FHIR Style | Our Style |
|---------|------------|-----------|
| Timestamps | `dateTime` | camelCase (`createdAt`) |
| References | `Reference(Type)` | Simplified object |
| Status codes | Hyphenated | Hyphenated (`in-progress`) |
| Field names | camelCase | camelCase |

---

## Summary: What We're Borrowing from FHIR

### Adopted Directly
- Field naming patterns (camelCase)
- `period.start` / `period.end` structure for time ranges
- `status` concept for lifecycle management
- Reference pattern for entity relationships
- `birthDate` field name

### Adapted/Simplified
- Status code values (reduced set)
- Name structure (single `name` vs multiple)
- Address structure (single vs multiple)
- Telecom (flattened vs ContactPoint array)
- Document content (direct vs attachment wrapper)

### Added (Not in FHIR)
- `meta.source` for data provenance tracking
- `meta.createdAt` / `meta.updatedAt` audit timestamps
- Scheduled vs actual times for sessions
- `no-show` status for sessions
- `archived` status for documents

---

## References

- [HL7 FHIR R4 Patient](https://hl7.org/fhir/R4/patient.html)
- [HL7 FHIR R4 Encounter](https://hl7.org/fhir/R4/encounter.html)
- [HL7 FHIR R4 DocumentReference](https://hl7.org/fhir/R4/documentreference.html)
