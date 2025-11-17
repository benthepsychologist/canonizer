# Questionnaire Canonicalization

## Overview

The Canonizer questionnaire schemas provide a standardized way to represent psychological and clinical assessment instruments and their responses. This enables transformation of form responses from various sources (Google Forms, Typeform, Qualtrics, etc.) into a canonical format for analysis, scoring, and long-term storage.

## Why Questionnaire Canonicalization?

**The Problem:**
- Assessment data comes from multiple sources (Google Forms, survey platforms, EHR systems)
- Each source has a different format and structure
- Question text is embedded in column headers making data hard to process
- Responses are text labels instead of numeric codes
- No standardized way to store scoring rules and interpretation guidelines

**The Solution:**
- **Questionnaire schema**: Defines the instrument (items, anchors, scoring rules)
- **QuestionnaireResponse schema**: Stores actual responses in a normalized format
- **Transforms**: Convert from source formats (Google Forms) to canonical format

## Schema Architecture

### 1. Questionnaire (Instrument Definition)

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

### 2. QuestionnaireResponse (Actual Responses)

**Purpose**: Stores responses from a person completing one or more questionnaires

**Schema**: `org.canonical/questionnaire_response/jsonschema/1-0-0`

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

### 3. Google Forms Response (Source Format)

**Purpose**: Raw FormResponse from Google Forms API v1

**Schema**: `com.google/forms_response/jsonschema/1-0-0`

**Characteristics**:
- Structured JSON with formId, responseId, timestamps
- Answers keyed by question ID (not question text)
- Values are text answers in nested structure
- Supports file uploads and grading
- Official Google Forms API format (not Sheets export)

**Example**:
```json
{
  "formId": "1FAIpQLSe...",
  "responseId": "ACYDBNj...",
  "createTime": "2024-03-31T17:52:00Z",
  "lastSubmittedTime": "2024-03-31T17:52:00Z",
  "respondentEmail": "example@example.com",
  "answers": {
    "1a2b3c4d": {
      "questionId": "1a2b3c4d",
      "textAnswers": {
        "answers": [{"value": "Never"}]
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

## Transformation Flow

```
Google Forms → QuestionnaireResponse(s)
     ↓                    ↓
  Raw form      Canonical normalized
  export         responses with
  (messy)        scoring/interpretation
```

### Transform Requirements

A transform from Google Forms API to QuestionnaireResponse must:

1. **Map question IDs to questionnaire items** using a question mapping configuration
2. **Extract text answer values** from nested textAnswers.answers structure
3. **Map text responses to numeric values** using Questionnaire.anchors
4. **Extract respondent metadata** (respondentEmail, createTime)
5. **Group items by questionnaire** (one form may contain multiple questionnaires)
6. **Compute scores** (optional) using Questionnaire.scores rules
7. **Handle missing/incomplete** responses gracefully

**Note**: The transform requires a mapping file that associates Google Forms question IDs to canonical questionnaire items (e.g., "1a2b3c4d" → "phq_9_1").

## Use Cases

### 1. Measurement-Based Care (MBC)

**Scenario**: Therapist collects PHQ-9, GAD-7, and custom measures every session

**Workflow**:
1. Client completes Google Form with multiple questionnaires
2. Response exported to Google Sheets
3. Transform converts to canonical QuestionnaireResponse
4. Scoring engine computes subscales and interpretations
5. Clinician dashboard visualizes trends over time

**Benefits**:
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

### Complete Transformation Example

**Input** (Google Forms API):
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

**Mapping** (question ID → questionnaire item):
```json
{
  "1a2b3c4d": "phq_9_1",
  "5e6f7g8h": "phq_9_2"
}
```

**Output** (QuestionnaireResponse):
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
