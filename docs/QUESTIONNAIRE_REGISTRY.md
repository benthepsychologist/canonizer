# Questionnaire Registry & Canonical Format

## Overview

The canonical questionnaire schema (`questionnaire_v1-0-0.json`) provides a standardized format for validated psychological and clinical assessment instruments. This enables:

- **Consistent scoring** across different administration platforms
- **Registry of validated instruments** with psychometric properties
- **Automated interpretation** with clinical ranges
- **Proper handling of reverse-scored items** and recoding
- **Source independence** (Google Forms, Qualtrics, paper → canonical)

---

## Schema Structure

### Core Components

1. **Metadata** - Questionnaire identification and citation
2. **Administration** - Instructions and formatting
3. **Scale** - Response format (Likert, binary, etc.)
4. **Items** - Questions with recoding rules
5. **Scores** - Subscales and composites with algorithms
6. **Validation** - Psychometric properties and norms
7. **Source** - Data lineage tracking

---

## Recoding & Reverse Scoring

### Why Recoding Matters

Many questionnaires include **reverse-scored items** to reduce response bias. For example:

**Depression Questionnaire:**
- Item 1: "I feel sad" (0=Never, 4=Always) → Higher = worse
- Item 2: "I feel happy" (0=Never, 4=Always) → Higher = BETTER (needs reversal!)

To score correctly, Item 2 must be **recoded** so that higher values still indicate worse depression:
- Response 0 (Never happy) → Score 4 (very depressed)
- Response 4 (Always happy) → Score 0 (not depressed)

### Recoding Methods

#### Method 1: Item-Level Reverse Scoring

Set `reverse_scored: true` on individual items:

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
  ]
}
```

#### Method 2: Subscale-Level Reversal

Specify reversed items in subscale scoring:

```json
{
  "scores": {
    "depression_total": {
      "included_items": [1, 2, 3, 4, 5],
      "reversed_items": [2, 5],
      "recoding": {
        "2": {
          "method": "reverse",
          "formula": "4 - value"
        },
        "5": {
          "method": "reverse",
          "formula": "4 - value"
        }
      }
    }
  }
}
```

#### Method 3: Custom Mapping

For non-linear recoding:

```json
{
  "item_number": 3,
  "recoding": {
    "method": "custom_map",
    "map": {
      "0": 4,
      "1": 3,
      "2": 2,
      "3": 1,
      "4": 0
    }
  }
}
```

---

## Example: FSCRS (Forms of Self-Criticizing/Attacking and Self-Reassuring Scale)

### Full Canonical Format

```json
{
  "questionnaire_id": "fscrs",
  "version": "1.0.0",
  "metadata": {
    "name": "Forms of Self-Criticizing/Attacking and Self-Reassuring Scale",
    "short_name": "FSCRS",
    "description": "The FSCRS measures self-criticism (inadequate self and hated self) and self-reassurance. Self-criticism relates to depression and anxiety; self-reassurance is protective and trainable.",
    "interpretation": "Higher inadequacy and self-hatred scores indicate problematic self-criticism. Higher self-reassurance indicates adaptive self-support. Self-criticism composite combines inadequacy and hatred subscales.",
    "citation": "Gilbert, P., Clarke, M., Hempel, S., Miles, J. N., & Irons, C. (2004). Criticizing and reassuring oneself: An exploration of forms, styles and reasons in female students. British Journal of Clinical Psychology, 43(1), 31-50.",
    "doi": "10.1348/014466504772812959",
    "license": "research_only",
    "language": "en"
  },
  "administration": {
    "instructions": "When things go wrong for me:",
    "time_estimate_minutes": 5,
    "item_prefix": "fscrs_",
    "item_numbering": "numeric"
  },
  "scale": {
    "type": "likert",
    "anchors": {
      "min": 0,
      "max": 4,
      "labels": {
        "0": "Not at all like me",
        "1": "A little bit like me",
        "2": "Moderately like me",
        "3": "Quite a bit like me",
        "4": "Extremely like me"
      }
    }
  },
  "items": [
    {
      "item_number": 1,
      "text": "I am easily disappointed with myself",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 2,
      "text": "There is a part of me that puts me down",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 3,
      "text": "I am able to remind myself of positive things about myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 4,
      "text": "I find it difficult to control my anger and frustration at myself",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 5,
      "text": "I find it easy to forgive myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 6,
      "text": "There is a part of me that feels I am not good enough",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 7,
      "text": "I feel beaten down by my own self-critical thoughts",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 8,
      "text": "I still like being me",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 9,
      "text": "I have become so angry with myself that I want to hurt or injure myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_hatred", "fscrs_self_criticism"]
    },
    {
      "item_number": 10,
      "text": "I have a sense of disgust with myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_hatred", "fscrs_self_criticism"]
    },
    {
      "item_number": 11,
      "text": "I can still feel lovable and acceptable",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 12,
      "text": "I stop caring about myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_hatred", "fscrs_self_criticism"]
    },
    {
      "item_number": 13,
      "text": "I find it easy to like myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 14,
      "text": "I remember and dwell on my failings",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 15,
      "text": "I call myself names",
      "reverse_scored": false,
      "subscales": ["fscrs_self_hatred", "fscrs_self_criticism"]
    },
    {
      "item_number": 16,
      "text": "I am gentle and supportive with myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 17,
      "text": "I can't accept failures and setbacks without feeling inadequate",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 18,
      "text": "I think I deserve my self-criticism",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 19,
      "text": "I am able to care and look after myself",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 20,
      "text": "There is a part of me that wants to get rid of the bits I don't like",
      "reverse_scored": false,
      "subscales": ["fscrs_inadequacy", "fscrs_self_criticism"]
    },
    {
      "item_number": 21,
      "text": "I encourage myself for the future",
      "reverse_scored": false,
      "subscales": ["fscrs_self_reassurance"]
    },
    {
      "item_number": 22,
      "text": "I do not like being me",
      "reverse_scored": false,
      "subscales": ["fscrs_self_hatred", "fscrs_self_criticism"]
    }
  ],
  "scores": {
    "fscrs_inadequacy": {
      "name": "Inadequate Self",
      "description": "Feelings of inadequacy and failure when things go wrong",
      "included_items": [1, 2, 4, 6, 7, 14, 17, 18, 20],
      "reversed_items": [],
      "scoring": {
        "method": "sum",
        "min": 0,
        "max": 36,
        "higher_is_better": false,
        "note": "Inadequate self subscale: feelings of inadequacy and failure"
      },
      "ranges": [
        {
          "min": 0,
          "max": 15,
          "label": "Low Inadequacy",
          "severity": "minimal",
          "description": "Minimal feelings of inadequacy",
          "color": "#4CAF50"
        },
        {
          "min": 16,
          "max": 25,
          "label": "Moderate Inadequacy",
          "severity": "moderate",
          "description": "Some self-critical thoughts about inadequacy",
          "color": "#FFC107"
        },
        {
          "min": 26,
          "max": 36,
          "label": "High Inadequacy",
          "severity": "severe",
          "description": "Significant feelings of inadequacy - target for intervention",
          "action": "Consider compassion-focused therapy or cognitive restructuring",
          "color": "#F44336"
        }
      ],
      "reliability": {
        "cronbach_alpha": 0.90
      }
    },
    "fscrs_self_hatred": {
      "name": "Hated Self",
      "description": "Self-hatred and desire to hurt oneself",
      "included_items": [9, 10, 12, 15, 22],
      "reversed_items": [],
      "scoring": {
        "method": "sum",
        "min": 0,
        "max": 20,
        "higher_is_better": false,
        "note": "Hated self subscale: self-hatred and desire to hurt oneself"
      },
      "ranges": [
        {
          "min": 0,
          "max": 4,
          "label": "Low Self-Hatred",
          "severity": "minimal",
          "description": "Minimal self-hatred",
          "color": "#4CAF50"
        },
        {
          "min": 5,
          "max": 9,
          "label": "Moderate Self-Hatred",
          "severity": "moderate",
          "description": "Some self-attacking thoughts",
          "color": "#FFC107"
        },
        {
          "min": 10,
          "max": 20,
          "label": "High Self-Hatred",
          "severity": "severe",
          "description": "Significant self-hatred - clinical attention needed",
          "action": "Immediate clinical attention recommended. Assess for self-harm risk.",
          "color": "#F44336"
        }
      ],
      "reliability": {
        "cronbach_alpha": 0.86
      }
    },
    "fscrs_self_reassurance": {
      "name": "Self-Reassurance",
      "description": "Ability to be kind and supportive to oneself",
      "included_items": [3, 5, 8, 11, 13, 16, 19, 21],
      "reversed_items": [],
      "scoring": {
        "method": "sum",
        "min": 0,
        "max": 32,
        "higher_is_better": true,
        "note": "Self-reassurance subscale: ability to be kind and supportive to oneself"
      },
      "ranges": [
        {
          "min": 0,
          "max": 14,
          "label": "Low Self-Reassurance",
          "severity": "low",
          "description": "Difficulty being self-supportive - key target for compassion training",
          "action": "Focus on self-compassion skills training",
          "color": "#F44336"
        },
        {
          "min": 15,
          "max": 20,
          "label": "Moderate Self-Reassurance",
          "severity": "moderate",
          "description": "Some capacity for self-support",
          "color": "#FFC107"
        },
        {
          "min": 21,
          "max": 32,
          "label": "High Self-Reassurance",
          "severity": "high",
          "description": "Strong self-compassion and support",
          "color": "#4CAF50"
        }
      ],
      "reliability": {
        "cronbach_alpha": 0.86
      }
    },
    "fscrs_self_criticism": {
      "name": "Self-Criticism Composite",
      "description": "Combined inadequacy and hatred subscales",
      "included_items": [1, 2, 4, 6, 7, 9, 10, 12, 14, 15, 17, 18, 20, 22],
      "reversed_items": [],
      "scoring": {
        "method": "sum",
        "min": 0,
        "max": 56,
        "higher_is_better": false,
        "note": "Self-criticism composite: combined inadequacy and hatred subscales"
      },
      "ranges": [
        {
          "min": 0,
          "max": 14,
          "label": "Low Self-Criticism",
          "severity": "minimal",
          "description": "Minimal self-critical tendencies",
          "color": "#4CAF50"
        },
        {
          "min": 15,
          "max": 24,
          "label": "Moderate Self-Criticism",
          "severity": "moderate",
          "description": "Some self-criticism present",
          "color": "#FFC107"
        },
        {
          "min": 25,
          "max": 56,
          "label": "High Self-Criticism",
          "severity": "severe",
          "description": "Significant self-criticism - primary target for therapy",
          "action": "Recommend compassion-focused therapy or CBT targeting self-criticism",
          "color": "#F44336"
        }
      ]
    }
  },
  "validation": {
    "validated_populations": [
      "female_university_students",
      "clinical_depression",
      "general_adult"
    ],
    "normative_data": {
      "fscrs_inadequacy": {
        "mean": 18.6,
        "sd": 7.2,
        "sample_size": 246,
        "population": "female_university_students"
      },
      "fscrs_self_hatred": {
        "mean": 5.8,
        "sd": 4.1,
        "sample_size": 246,
        "population": "female_university_students"
      },
      "fscrs_self_reassurance": {
        "mean": 19.4,
        "sd": 5.9,
        "sample_size": 246,
        "population": "female_university_students"
      }
    }
  },
  "source": {
    "platform": "questionnaire_registry",
    "platform_version": "1.0.0",
    "registry_url": "https://github.com/yourusername/questionnaire-registry"
  }
}
```

### Key Points About FSCRS Recoding

**The FSCRS has NO reverse-scored items!** All `reversed_items` arrays are empty because:

1. **Self-Criticism Items** (Inadequacy + Self-Hatred):
   - "I am easily disappointed with myself"
   - Higher response = More self-criticism = Worse
   - No reversal needed

2. **Self-Reassurance Items**:
   - "I am able to remind myself of positive things"
   - Higher response = More self-reassurance = Better
   - No reversal needed (subscale interpretation differs)

The difference is in the **subscale interpretation** (`higher_is_better` flag), not in item recoding.

---

## Example: PHQ-9 (With Reverse Scoring)

Some questionnaires DO have reverse-scored items. Here's a hypothetical example:

```json
{
  "questionnaire_id": "example_reversed",
  "items": [
    {
      "item_number": 1,
      "text": "Little interest or pleasure in doing things",
      "reverse_scored": false
    },
    {
      "item_number": 2,
      "text": "Feeling good about yourself",
      "reverse_scored": true,
      "recoding": {
        "method": "reverse",
        "formula": "3 - value"
      }
    }
  ],
  "scores": {
    "total": {
      "included_items": [1, 2],
      "reversed_items": [2],
      "recoding": {
        "2": {
          "method": "reverse",
          "formula": "3 - value"
        }
      }
    }
  }
}
```

---

## Usage in Transforms

### Google Forms → Canonical Questionnaire

```jsonata
{
  "questionnaire_id": "fscrs",
  "version": "1.0.0",
  "response_id": responseId,
  "responses": [$each(answers, function($v, $k) {
    {
      "item_number": $number($substring($v.questionId, 6)),
      "response_value": $number($v.textAnswers.answers[0].value)
    }
  })],
  "source": {
    "platform": "google_forms",
    "platform_version": "v1"
  }
}
```

---

## Best Practices

### 1. Always Document Recoding

```json
"recoding": {
  "method": "reverse",
  "formula": "max - value"
}
```

### 2. Specify Reversal at Both Levels

- **Item level**: For display and understanding
- **Subscale level**: For actual computation

### 3. Include Psychometric Properties

```json
"reliability": {
  "cronbach_alpha": 0.90,
  "test_retest": 0.85
}
```

### 4. Provide Clinical Context

```json
"ranges": [
  {
    "min": 10,
    "max": 20,
    "label": "Severe",
    "action": "Immediate clinical attention recommended"
  }
]
```

---

## Registry Structure

```
questionnaire-registry/
├── questionnaires/
│   ├── fscrs/
│   │   ├── 1.0.0/
│   │   │   ├── questionnaire.json    # Canonical format
│   │   │   ├── scoring.jsonata       # Scoring algorithm
│   │   │   └── tests/
│   │   │       ├── sample_responses.json
│   │   │       └── expected_scores.json
│   ├── phq9/
│   ├── gad7/
│   └── ...
└── registry.json                     # Index
```

---

## See Also

- `transforms/schemas/canonical/questionnaire_v1-0-0.json` - Full schema
- `transforms/schemas/canonical/form_response_v1-0-0.json` - Response data schema
- `docs/REGISTRY.md` - Transform registry guide
