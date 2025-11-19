# Questionnaire Registry

A registry of validated psychological and clinical assessment instruments in canonical format.

## Structure

```
questionnaire_registry/
├── fscrs/
│   └── 1.0.0/
│       ├── questionnaire.json      # Canonical questionnaire definition
│       ├── scoring.jsonata         # (Optional) Scoring algorithm
│       └── tests/                  # (Optional) Test fixtures
├── phq9/
├── gad7/
└── registry.json                   # Index of all questionnaires
```

## Questionnaire Format

Each questionnaire is defined in the canonical format following `transforms/schemas/canonical/questionnaire_v1-0-0.json`.

### Required Components

1. **Metadata** - Name, description, citation, license
2. **Administration** - Instructions, timing, item prefixes
3. **Scale** - Response format (Likert, binary, etc.)
4. **Items** - Questions with reverse-scoring flags
5. **Scores** - Subscales with scoring algorithms and ranges
6. **Validation** - Psychometric properties and norms
7. **Source** - Data lineage

## Example: FSCRS

Forms of Self-Criticizing/Attacking and Self-Reassuring Scale

**File:** `fscrs/1.0.0/questionnaire.json`

**Subscales:**
- Inadequate Self (9 items)
- Hated Self (5 items)
- Self-Reassurance (8 items)
- Self-Criticism Composite (14 items)

**Features:**
- 22 items, 5-point Likert scale
- No reverse-scored items (different subscale interpretations)
- Clinical cutoffs with severity labels
- Normative data from original study
- Psychometric properties (Cronbach's alpha)

## Using Questionnaires

### 1. Load from Registry

```python
import json

# Load questionnaire definition
with open('questionnaire_registry/fscrs/1.0.0/questionnaire.json') as f:
    questionnaire = json.load(f)

# Get items
for item in questionnaire['items']:
    print(f"{item['item_number']}. {item['text']}")
```

### 2. Score Responses

```python
def score_subscale(responses, subscale_def):
    """Score a subscale given response data."""
    score = 0
    for item_num in subscale_def['included_items']:
        value = responses[f"fscrs_{item_num}"]

        # Apply reverse scoring if needed
        if item_num in subscale_def.get('reversed_items', []):
            max_val = questionnaire['scale']['anchors']['max']
            value = max_val - value

        score += value

    return score

# Example usage
responses = {
    "fscrs_1": 2,
    "fscrs_2": 3,
    # ... all 22 items
}

inadequacy_score = score_subscale(
    responses,
    questionnaire['scores']['fscrs_inadequacy']
)
```

### 3. Interpret Scores

```python
def interpret_score(score, subscale_def):
    """Get clinical interpretation for a score."""
    for range_def in subscale_def['ranges']:
        if range_def['min'] <= score <= range_def['max']:
            return {
                'score': score,
                'label': range_def['label'],
                'severity': range_def['severity'],
                'description': range_def['description'],
                'action': range_def.get('action', '')
            }

result = interpret_score(inadequacy_score, questionnaire['scores']['fscrs_inadequacy'])
print(f"Score: {result['score']}")
print(f"Interpretation: {result['label']} - {result['description']}")
```

## Recoding & Reverse Scoring

### No Recoding Needed (FSCRS)

FSCRS has no reverse-scored items. The self-reassurance items are naturally positive:
- "I am able to remind myself of positive things" → Higher = Better

The self-criticism items are naturally negative:
- "I am easily disappointed with myself" → Higher = Worse

Interpretation differs by subscale (`higher_is_better` flag), not by item recoding.

### Reverse Scoring Example

Some questionnaires DO require reverse scoring:

```json
{
  "items": [
    {
      "item_number": 1,
      "text": "I feel sad",
      "reverse_scored": false
    },
    {
      "item_number": 2,
      "text": "I feel happy",
      "reverse_scored": true,
      "recoding": {
        "method": "reverse",
        "formula": "max - value"
      }
    }
  ],
  "scores": {
    "depression_total": {
      "included_items": [1, 2],
      "reversed_items": [2],
      "recoding": {
        "2": {
          "method": "reverse",
          "formula": "4 - value"
        }
      }
    }
  }
}
```

## Adding New Questionnaires

### 1. Create Directory

```bash
mkdir -p questionnaire_registry/{questionnaire_id}/1.0.0
```

### 2. Define Questionnaire

Create `questionnaire.json` following the canonical schema.

**Required fields:**
- `questionnaire_id`
- `version`
- `metadata` (name, description)
- `items` (array of questions)
- `scores` (subscales with algorithms)
- `source`

**Recommended fields:**
- `scale` (response format)
- `administration` (instructions, timing)
- `validation` (psychometric properties)

### 3. Validate

```bash
can validate run \
  --schema transforms/schemas/canonical/questionnaire_v1-0-0.json \
  --data questionnaire_registry/{questionnaire_id}/1.0.0/questionnaire.json
```

### 4. Add to Index

Update `registry.json`:

```json
{
  "questionnaires": [
    {
      "id": "fscrs",
      "name": "FSCRS",
      "versions": ["1.0.0"],
      "latest": "1.0.0"
    }
  ]
}
```

## Available Questionnaires

| ID | Name | Version | Items | Subscales | License |
|----|------|---------|-------|-----------|---------|
| fscrs | Forms of Self-Criticizing/Attacking and Self-Reassuring Scale | 1.0.0 | 22 | 4 | research_only |

## Psychometric Properties

All questionnaires in this registry include:
- **Reliability**: Cronbach's alpha, test-retest coefficients
- **Validity**: Validated populations
- **Norms**: Normative data (mean, SD, sample size)
- **Clinical Cutoffs**: Severity ranges with interpretations

## License & Usage

Each questionnaire has its own license:
- `public_domain` - Free to use
- `creative_commons` - Attribution required
- `research_only` - Research use only, clinical use may require permission
- `proprietary` - Contact rights holder

**FSCRS**: Research use only. Clinical use may require permission from authors.

## References

**FSCRS:**
Gilbert, P., Clarke, M., Hempel, S., Miles, J. N., & Irons, C. (2004). Criticizing and reassuring oneself: An exploration of forms, styles and reasons in female students. *British Journal of Clinical Psychology, 43*(1), 31-50.
https://doi.org/10.1348/014466504772812959

## See Also

- `transforms/schemas/canonical/questionnaire_v1-0-0.json` - Canonical schema
- `docs/QUESTIONNAIRE_REGISTRY.md` - Detailed documentation
- `transforms/forms/google_forms_to_canonical/` - Form response transforms
