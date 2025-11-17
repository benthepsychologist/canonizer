# Questionnaire Canonicalization

## Overview

This document describes a **two-layer architecture** for working with assessment data:

1. **Layer 1 (Canonizer)**: Schema transformation - normalizing form platforms
2. **Layer 2 (Processing)**: Data transformation - extracting questionnaire data

Understanding this separation is critical: **Canonizer handles schema normalization, not questionnaire extraction.**

## The Two-Layer Architecture

### Layer 1: Form Response Canonicalization (Schema Transform)

**What it does**: Normalizes different form platforms into a consistent structure

**Transform examples**:
```
Google Forms API     → org.canonical/form_response
Typeform API         → org.canonical/form_response
Microsoft Forms API  → org.canonical/form_response
```

**Responsibility**: Platform-agnostic form submissions (question ID → answer value)
**Tools**: Canonizer (this project)
**Knows about**: Forms, questions, answers
**Doesn't know about**: Questionnaires, scoring, subscales

### Layer 2: Questionnaire Extraction (Data Processing)

**What it does**: Extracts questionnaire data from normalized form responses

**Transform example**:
```
org.canonical/form_response
  + question mapping config
  + questionnaire registry
  → org.canonical/questionnaire_response(s)
```

**Responsibility**: Extract questionnaires, compute scores, apply interpretations
**Tools**: Separate scoring/processing service (not Canonizer)
**Knows about**: Questionnaires, scoring rules, subscales, interpretation
**Doesn't know about**: Source platforms

## Why This Separation?

**The Problem:**
- Assessment data comes from multiple platforms (Google Forms, Typeform, Qualtrics)
- Each platform has a different API format
- Forms often contain multiple questionnaires (PHQ-9 + GAD-7 + custom questions)
- Questionnaire scoring requires domain knowledge (reverse items, subscales, ranges)
- A single "transform" can't handle both platform normalization AND questionnaire extraction

**The Solution:**
- **Layer 1**: Canonizer normalizes platform differences (schema transform)
- **Layer 2**: Scoring engine extracts questionnaires (data processing)
- Clean separation of concerns: platform knowledge vs. domain knowledge

## Schema Architecture

This project defines schemas for BOTH layers:

### Layer 1 Schemas (Canonizer - Schema Transform)

#### 1. FormResponse (Canonical Form Submission)

**Purpose**: Platform-agnostic representation of a form submission

**Schema**: `org.canonical/form_response/jsonschema/1-0-0`

**Used for**: Target of schema transforms from all form platforms

**Key Components**:
- **response_id**: Unique identifier
- **form_id** and **form_name**: Which form was submitted
- **submitted_at**: ISO 8601 timestamp
- **source**: Platform info (google_forms, typeform, etc.)
- **respondent**: Email, name, external_id
- **answers**: Array of question-answer pairs
  - `question_id`: Platform-specific question identifier
  - `question_text`: Human-readable question (optional)
  - `answer_value`: The raw answer (text, number, array, etc.)
  - `answer_type`: Type classification (choice, text, scale, etc.)
  - `answer_text`: Human-readable answer text

**Example**:
```json
{
  "response_id": "ACYDBNj_xyz789",
  "form_id": "1FAIpQLSe_abc123",
  "form_name": "MBC Initial Assessment",
  "submitted_at": "2024-05-22T15:09:51Z",
  "source": {
    "platform": "google_forms",
    "platform_version": "v1"
  },
  "respondent": {
    "email": "client@example.com"
  },
  "answers": [
    {
      "question_id": "1a2b3c4d",
      "question_text": "Little interest or pleasure in doing things",
      "answer_value": "Not at all",
      "answer_type": "choice"
    },
    {
      "question_id": "5e6f7g8h",
      "question_text": "Feeling down, depressed, or hopeless",
      "answer_value": "Several days",
      "answer_type": "choice"
    }
  ]
}
```

#### 2. Google Forms Response (Source Format)

**Purpose**: Raw FormResponse from Google Forms API v1

**Schema**: `com.google/forms_response/jsonschema/1-0-0`

**Used for**: Input to Canonizer transforms

See full example in Layer 1 Examples section below.

### Layer 2 Schemas (Processing - Data Transform)

#### 3. Questionnaire (Instrument Definition)

**Purpose**: Defines the structure, scoring, and interpretation of an assessment instrument

**Schema**: `org.canonical/questionnaire/jsonschema/1-0-0`

**Key Components**:
- **Basic metadata**: id, name, description, version
- **Items**: Array of questions with item numbers and text
- **Anchors**: Response scale definition (e.g., 0="Not at all", 3="Nearly every day")
- **Scores**: Scoring rules for subscales and composite scores
  - `included_items`: Which items contribute to this score
  - `reversed_items`: Items that are reverse-scored
  - `scoring.method`: How to compute (sum, average, sum_then_double, etc.)
  - `ranges`: Interpretation ranges (minimal, mild, moderate, severe)

**Example** (PHQ-9):
```json
{
  "id": "phq_9",
  "name": "Patient Health Questionnaire-9",
  "description": "Self-report questionnaire measuring depression severity...",
  "version": "1.0",
  "items": [
    {
      "item_number": 1,
      "text": "Little interest or pleasure in doing things"
    }
  ],
  "anchors": {
    "min": 0,
    "max": 3,
    "labels": {
      "0": "Not at all",
      "1": "Several days",
      "2": "More than half the days",
      "3": "Nearly every day"
    }
  },
  "scores": {
    "phq_9": {
      "included_items": [1, 2, 3, 4, 5, 6, 7, 8, 9],
      "reversed_items": [],
      "scoring": {
        "method": "sum",
        "min": 0,
        "max": 27,
        "higher_is_better": false
      },
      "ranges": [
        {
          "min": 0,
          "max": 4,
          "label": "Minimal",
          "severity": "minimal",
          "description": "Minimal or no depression"
        }
      ]
    }
  }
}
```

#### 4. QuestionnaireResponse (Extracted Questionnaire Data)

**Purpose**: Stores questionnaire-specific responses extracted and scored from form submissions

**Schema**: `org.canonical/questionnaire_response/jsonschema/1-0-0`

**Used for**: Output of Layer 2 processing

**Key Components**:
- **response_id**: Unique identifier for this response session
- **authored**: ISO 8601 timestamp
- **source**: Where the response came from (Google Forms, etc.)
- **respondent**: Person who completed the questionnaire (with privacy considerations)
- **questionnaires**: Array of completed questionnaires
  - `questionnaire_id`: References the Questionnaire definition
  - `item_responses`: Map of item_id → response value (numeric)
  - `scores`: Optional pre-computed scores with interpretations
  - `completed`: Whether all required items were answered

**Example**:
```json
{
  "response_id": "resp_20240331_001",
  "authored": "2024-03-31T17:52:00Z",
  "source": {
    "system": "google_forms",
    "form_name": "mbc_initial"
  },
  "respondent": {
    "id": "client_123",
    "email": "example@example.com"
  },
  "questionnaires": [
    {
      "questionnaire_id": "phq_9",
      "questionnaire_version": "1.0",
      "item_responses": {
        "phq_9_1": 0,
        "phq_9_2": 1,
        "phq_9_3": 2
      },
      "scores": {
        "phq_9": {
          "value": 12,
          "interpretation": {
            "label": "Moderate",
            "severity": "moderate",
            "description": "Moderate depression"
          }
        }
      },
      "completed": true
    }
  ]
}
```

## Transformation Flow

### Layer 1: Schema Transform (Canonizer)

```
Google Forms API → org.canonical/form_response
     |                        |
   Source              Platform-agnostic
  platform              form submission
  specific
```

**Canonizer Transform Requirements**:
1. **Extract response metadata** (formId → form_id, responseId → response_id, createTime → submitted_at)
2. **Extract respondent info** (respondentEmail → respondent.email)
3. **Flatten answer structure** (nested textAnswers.answers → flat answers array)
4. **Preserve question IDs** (questionId → question_id)
5. **Tag platform source** (source.platform = "google_forms")

**What it does NOT do**:
- Does not know about questionnaires (PHQ-9, GAD-7, etc.)
- Does not map questions to questionnaire items
- Does not convert text to numeric values
- Does not compute scores

### Layer 2: Data Processing (Separate Tool)

```
org.canonical/form_response
  + question_mapping.json (maps question IDs to questionnaire items)
  + questionnaire_registry (PHQ-9, GAD-7 definitions)
  ↓
org.canonical/questionnaire_response(s)
     |
  Extracted,
  scored questionnaires
  with interpretations
```

**Processing Requirements**:
1. **Load question mapping** (question_id → questionnaire_item mapping)
2. **Load questionnaire definitions** from registry
3. **Map text responses to numeric values** using Questionnaire.anchors
4. **Group items by questionnaire** (one form contains multiple questionnaires)
5. **Compute scores** using Questionnaire.scores rules
6. **Apply interpretation ranges** to computed scores
7. **Handle reverse-scored items** correctly
8. **Handle missing/incomplete** responses gracefully

**Example Mapping File**:
```json
{
  "form_id": "1FAIpQLSe_abc123",
  "form_name": "MBC Initial Assessment",
  "question_mappings": [
    {"question_id": "1a2b3c4d", "questionnaire_item": "phq_9_1"},
    {"question_id": "5e6f7g8h", "questionnaire_item": "phq_9_2"},
    {"question_id": "9i0j1k2l", "questionnaire_item": "gad_7_1"}
  ]
}
```

## Use Cases

### 1. Measurement-Based Care (MBC)

**Scenario**: Therapist collects PHQ-9, GAD-7, and custom measures every session

**Workflow**:
1. Client completes Google Form with multiple questionnaires
2. **Layer 1 (Canonizer)**: Google Forms API response → canonical form_response
3. **Layer 2 (Processor)**: form_response → questionnaire_response(s) with scores
4. Clinician dashboard visualizes trends over time

**Benefits**:
- Platform-agnostic: Can switch from Google Forms to Typeform without changing downstream processing
- Consistent scoring across all sessions
- Easy to add new questionnaires to battery
- Historical data remains valid as forms evolve

### 2. Research Data Collection

**Scenario**: Research study using standardized instruments across sites

**Workflow**:
1. Each site uses their preferred platform (Google Forms, Qualtrics, REDCap)
2. Site-specific transforms to canonical format
3. Centralized analysis using consistent schema

**Benefits**:
- Multi-site studies without format conflicts
- Standardized scoring and interpretation
- Easy to validate data quality

### 3. Clinical Registry

**Scenario**: Maintain registry of assessments for regulatory compliance

**Workflow**:
1. Store Questionnaire definitions in registry
2. Store QuestionnaireResponses linked to patient records
3. Audit trail of when/where assessments were completed

**Benefits**:
- Immutable assessment definitions with versioning
- Clear provenance (who completed when)
- Support for schema evolution (new items, revised scoring)

## Schema Versioning

Following Iglu SchemaVer (MODEL-REVISION-ADDITION):

- **MODEL change** (1-0-0 → 2-0-0): Breaking change, incompatible
  - Removing required field
  - Changing field type
  - Changing scoring algorithm fundamentally

- **REVISION change** (1-0-0 → 1-1-0): Compatible schema change
  - Adding new optional field
  - Relaxing validation rules

- **ADDITION change** (1-0-0 → 1-0-1): No schema change
  - Documentation updates
  - Example updates

### Questionnaire Versioning Best Practices

- **Instrument version** (e.g., PHQ-9 v1.0): Track official instrument revisions
- **Schema version** (1-0-0): Track schema format changes
- Never modify published Questionnaire definitions - create new version
- QuestionnaireResponse always references specific questionnaire_version

## Registry Integration

Questionnaires and their scoring rules can be stored in the canonizer registry:

```
canonizer-registry/
  questionnaires/
    phq_9/
      1.0.0/
        questionnaire.json
        metadata.yaml
    gad_7/
      1.0.0/
        questionnaire.json
        metadata.yaml
```

Commands:
```bash
# Validate a questionnaire definition
can registry validate questionnaire phq_9@1.0.0

# List available questionnaires
can registry list --type questionnaire

# Score a response against questionnaire
can score response.json --questionnaire phq_9@1.0.0
```

## Comparison to FHIR

The Canonizer questionnaire schemas are inspired by FHIR's Questionnaire and QuestionnaireResponse resources but simplified for specific use cases:

| Feature | FHIR | Canonizer |
|---------|------|-----------|
| **Questionnaire definition** | Yes (complex) | Yes (simplified) |
| **Item types** | Many types | Focus on Likert scales |
| **Scoring** | Extensions needed | Built-in support |
| **Interpretation ranges** | Not standardized | First-class support |
| **Skip logic** | Supported | Not yet |
| **Adaptive testing** | Possible | Not yet |
| **Complexity** | High (enterprise EHR) | Low (research/practice) |

**When to use FHIR instead**:
- Integration with full EHR system
- Need comprehensive FHIR ecosystem
- Complex adaptive questionnaires

**When to use Canonizer**:
- Research studies
- Measurement-based care in private practice
- Form data transformation pipelines
- Custom scoring algorithms

## Examples

### Layer 1: Schema Transform (Canonizer)

**Input** (Google Forms API - `com.google/forms_response`):
```json
{
  "formId": "1FAIpQLSe_abc123",
  "responseId": "ACYDBNj_xyz789",
  "createTime": "2024-05-22T15:09:51Z",
  "lastSubmittedTime": "2024-05-22T15:09:51Z",
  "respondentEmail": "client@example.com",
  "answers": {
    "1a2b3c4d": {
      "questionId": "1a2b3c4d",
      "textAnswers": {
        "answers": [{"value": "Not at all"}]
      }
    },
    "5e6f7g8h": {
      "questionId": "5e6f7g8h",
      "textAnswers": {
        "answers": [{"value": "Several days"}]
      }
    }
  }
}
```

**Transform**: `google_forms_to_canonical_form_response`

**Output** (Canonical Form Response - `org.canonical/form_response`):
```json
{
  "response_id": "ACYDBNj_xyz789",
  "form_id": "1FAIpQLSe_abc123",
  "submitted_at": "2024-05-22T15:09:51Z",
  "last_updated_at": "2024-05-22T15:09:51Z",
  "source": {
    "platform": "google_forms",
    "platform_version": "v1"
  },
  "respondent": {
    "email": "client@example.com"
  },
  "answers": [
    {
      "question_id": "1a2b3c4d",
      "answer_value": "Not at all",
      "answer_type": "choice"
    },
    {
      "question_id": "5e6f7g8h",
      "answer_value": "Several days",
      "answer_type": "choice"
    }
  ],
  "status": "submitted"
}
```

### Layer 2: Data Processing (Separate Tool)

**Input 1** (Canonical Form Response from Layer 1):
```json
{
  "response_id": "ACYDBNj_xyz789",
  "form_id": "1FAIpQLSe_abc123",
  "submitted_at": "2024-05-22T15:09:51Z",
  "answers": [
    {"question_id": "1a2b3c4d", "answer_value": "Not at all"},
    {"question_id": "5e6f7g8h", "answer_value": "Several days"}
  ]
}
```

**Input 2** (Question Mapping):
```json
{
  "form_id": "1FAIpQLSe_abc123",
  "question_mappings": [
    {"question_id": "1a2b3c4d", "questionnaire_item": "phq_9_1"},
    {"question_id": "5e6f7g8h", "questionnaire_item": "phq_9_2"}
  ]
}
```

**Input 3** (Questionnaire Definition):
```json
{
  "id": "phq_9",
  "anchors": {
    "labels": {
      "0": "Not at all",
      "1": "Several days"
    }
  }
}
```

**Processing**:
1. Map question IDs: "1a2b3c4d" → "phq_9_1", "5e6f7g8h" → "phq_9_2"
2. Map text to numeric: "Not at all" → 0, "Several days" → 1
3. Group by questionnaire: Both belong to phq_9
4. Compute scores: sum = 1 (incomplete, only 2 of 9 items)

**Output** (Questionnaire Response - `org.canonical/questionnaire_response`):
```json
{
  "response_id": "ACYDBNj_xyz789",
  "authored": "2024-05-22T15:09:51Z",
  "source": {
    "system": "google_forms",
    "form_id": "1FAIpQLSe_abc123"
  },
  "respondent": {
    "email": "client@example.com"
  },
  "questionnaires": [
    {
      "questionnaire_id": "phq_9",
      "questionnaire_version": "1.0",
      "item_responses": {
        "phq_9_1": 0,
        "phq_9_2": 1
      },
      "completed": false
    }
  ]
}
```

## Future Enhancements

- **Skip logic**: Conditional item display based on previous answers
- **Calculated items**: Items whose value is computed from other items
- **Adaptive testing**: CAT (Computerized Adaptive Testing) support
- **Multi-language**: Support for translated instruments
- **Item banks**: Share items across multiple questionnaires
- **Validation rules**: Min/max values, required patterns
- **Transform generation**: Auto-generate transforms from questionnaire definitions

## References

- **FHIR Questionnaire**: https://hl7.org/fhir/questionnaire.html
- **FHIR QuestionnaireResponse**: https://hl7.org/fhir/questionnaireresponse.html
- **Iglu Schema Registry**: https://github.com/snowplow/iglu
- **PHQ-9**: Kroenke et al. (2001) The PHQ-9: validity of a brief depression severity measure
- **GAD-7**: Spitzer et al. (2006) A brief measure for assessing generalized anxiety disorder

---

**Version**: 1.0
**Last Updated**: 2025-11-17
**Maintainer**: Canonizer Project
