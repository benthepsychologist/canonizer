"""Basic Canonizer usage examples."""

import json
from pathlib import Path

# Example 1: Simple canonicalization with registry-style ID
from canonizer import canonicalize

# Load raw data
raw_email = json.loads(Path("tests/golden/email/gmail_v1/input.json").read_text())

# Transform using registry-style transform ID
canonical = canonicalize(
    raw_email,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)

print("Example 1: Canonicalized email")
print(json.dumps(canonical, indent=2)[:200], "...")

# Example 2: Using convenience functions
from canonizer import canonicalize_email_from_gmail

canonical_lite = canonicalize_email_from_gmail(raw_email, format="lite")
canonical_full = canonicalize_email_from_gmail(raw_email, format="full")
canonical_minimal = canonicalize_email_from_gmail(raw_email, format="minimal")

print("\nExample 2: Different email formats")
print(f"Lite format keys: {list(canonical_lite.keys())}")
print(f"Full format keys: {list(canonical_full.keys())}")
print(f"Minimal format keys: {list(canonical_minimal.keys())}")

# Example 3: Batch processing
from canonizer import run_batch

# Process multiple emails at once
raw_emails = [raw_email, raw_email, raw_email]  # Example: 3 identical emails

canonicals = run_batch(
    raw_emails,
    transform_id="email/gmail_to_jmap_lite@1.0.0"
)

print(f"\nExample 3: Batch processed {len(canonicals)} emails")

# Example 4: Error handling
from canonizer.core.validator import ValidationError

try:
    invalid_data = {"invalid": "data"}
    canonical = canonicalize(
        invalid_data,
        transform_id="email/gmail_to_jmap_lite@1.0.0"
    )
except ValidationError as e:
    print(f"\nExample 4: Validation error caught: {e}")
except Exception as e:
    print(f"\nExample 4: Error caught: {e}")

# Example 5: Disable validation for performance
canonical_fast = canonicalize(
    raw_email,
    transform_id="email/gmail_to_jmap_lite@1.0.0",
    validate_input=False,  # Skip input validation
    validate_output=False,  # Skip output validation
)

print("\nExample 5: Fast mode (no validation) completed")

# Example 6: Using full path instead of registry ID
canonical_path = canonicalize(
    raw_email,
    transform_id="transforms/email/gmail_to_jmap_lite/1.0.0/spec.meta.yaml"
)

print("\nExample 6: Using full path completed")

print("\n✓ All examples completed successfully")
