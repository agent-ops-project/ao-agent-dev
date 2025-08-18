from telemetry.client import supabase_client


def store_run_result(user_id: str, session_id: str, sample_id: str, result: str) -> bool:
    """Store a run result in Supabase."""
    if not supabase_client.is_available():
        print("Supabase not available, skipping run result storage")
        return False

    try:
        supabase_client.client.table("run_results").insert(
            {"user_id": user_id, "session_id": session_id, "sample_id": sample_id, "result": result}
        ).execute()

        print(f"Run result stored: {sample_id} -> {result}")
        return True

    except Exception as e:
        print(f"Failed to store run result: {e}")
        return False


if __name__ == "__main__":
    print("Testing run results functionality...")

    test_user = "test_user_123"
    test_session = "test_session_456"

    # Test different types of results
    test_cases = [
        ("sample_001", "success"),
        ("sample_002", "failure"),
        ("sample_003", "timeout"),
        ("sample_004", "0.85"),  # Numeric result as string
        ("sample_005", "partial_success"),
    ]

    print(f"\nTesting {len(test_cases)} run result uploads...")

    for i, (sample_id, result) in enumerate(test_cases, 1):
        print(f"\n{i}. Testing sample '{sample_id}' with result '{result}'...")
        success = store_run_result(test_user, test_session, sample_id, result)
        if success:
            print(f"✅ Result stored successfully!")
        else:
            print(f"❌ Result storage failed")

    print("\nAll run result tests completed!")
