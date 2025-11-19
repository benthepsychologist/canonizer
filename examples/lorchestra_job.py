"""Example: How lorchestra jobs use Canonizer.

This file demonstrates the pattern for using Canonizer in lorchestra jobs.
This code does NOT run standalone - it requires lorchestra dependencies.

Key principle: Canonizer is a pure transformation library (JSON in, JSON out).
All orchestration logic (BQ queries, event emission) lives in lorchestra jobs.
"""

# This import works because Canonizer is a library
from canonizer import canonicalize, run_batch

# These imports are from lorchestra (NOT in Canonizer)
# from lorchestra.stack_clients.event_client import emit_event
# from lorchestra.stack_clients.bq_client import BigQueryClient


def canonicalize_email_from_events_job():
    """
    lorchestra job: Canonicalize email events from BigQuery.

    Flow:
      1. Query raw events from BQ (orchestration)
      2. Transform each with Canonizer (pure function)
      3. Emit canonical events (orchestration)
    """
    # 1. Query raw events (lorchestra concern)
    # bq = BigQueryClient(project="therapy-ai")
    # rows = bq.query('''
    #     SELECT * FROM raw_events
    #     WHERE event_type = 'email.gmail.raw'
    #     AND processed = FALSE
    #     LIMIT 100
    # ''').result()

    # Example: Simulate BQ results
    rows = [
        {"id": "event1", "payload": {"...": "gmail api data"}},
        {"id": "event2", "payload": {"...": "gmail api data"}},
    ]

    # 2. Transform each (pure Canonizer function call)
    for row in rows:
        try:
            # Pure transformation - no side effects
            canonical = canonicalize(
                row["payload"],
                transform_id="email/gmail_to_jmap_lite@1.0.0"
            )

            # 3. Emit canonical event (lorchestra concern)
            # emit_event(
            #     event_type="email.canonicalized",
            #     payload=canonical,
            #     metadata={
            #         "source_event_id": row["id"],
            #         "transform_id": "email/gmail_to_jmap_lite@1.0.0",
            #     }
            # )

            print(f"✓ Canonicalized event {row['id']}")

        except Exception as e:
            print(f"✗ Failed to canonicalize event {row['id']}: {e}")
            # emit_event("email.canonicalization_failed", payload={"error": str(e)})


def canonicalize_forms_batch_job():
    """
    lorchestra job: Batch canonicalize form responses.

    Uses run_batch() for efficient batch processing.
    """
    # 1. Query raw form events
    # bq = BigQueryClient(project="therapy-ai")
    # rows = bq.query('SELECT * FROM raw_events WHERE event_type = "form.submitted"').result()

    rows = [{"payload": {"form": "data"}} for _ in range(5)]

    # 2. Extract payloads for batch processing
    raw_forms = [row["payload"] for row in rows]

    # 3. Batch transform (single function call)
    try:
        canonicals = run_batch(
            raw_forms,
            transform_id="forms/google_forms_to_canonical@1.0.0"
        )

        # 4. Emit batch of canonical events
        for canonical in canonicals:
            # emit_event("form_response.canonicalized", payload=canonical)
            print(f"✓ Canonicalized form response")

    except Exception as e:
        print(f"✗ Batch canonicalization failed: {e}")


def handle_errors_gracefully():
    """
    lorchestra job: Handle partial failures in batch processing.

    Best practice: Collect errors, don't fail fast.
    """
    # rows = bq.query('SELECT * FROM raw_events WHERE ...').result()

    rows = [
        {"id": "1", "payload": {"valid": "data"}},
        {"id": "2", "payload": {"invalid": "data"}},  # Will fail
        {"id": "3", "payload": {"valid": "data"}},
    ]

    successes = []
    failures = []

    for row in rows:
        try:
            canonical = canonicalize(
                row["payload"],
                transform_id="email/gmail_to_jmap_lite@1.0.0"
            )

            # emit_event("email.canonicalized", payload=canonical)
            successes.append(row["id"])

        except Exception as e:
            # emit_event("email.canonicalization_failed", payload={...})
            failures.append({"event_id": row["id"], "error": str(e)})

    print(f"✓ Processed {len(successes)} events successfully")
    print(f"✗ Failed to process {len(failures)} events")


# The key insight:
#
# Canonizer responsibility:  raw_json + transform_id → canonical_json
# lorchestra responsibility: BQ queries, event emission, error handling, scheduling
#
# Clean separation of concerns.

if __name__ == "__main__":
    print("Example lorchestra job patterns:\n")
    print("1. Single-event canonicalization:")
    canonicalize_email_from_events_job()

    print("\n2. Batch canonicalization:")
    canonicalize_forms_batch_job()

    print("\n3. Error handling:")
    handle_errors_gracefully()

    print("\n✓ All job patterns demonstrated")
