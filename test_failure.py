
from app import orchestrator


# Simulate a validation failure.
# This function deliberately fails every time it is called.
def simulate_validation_failure(run_id):
    raise RuntimeError(
        "TEST FAILURE: Simulated validation service error"
    )


def main():

    print("\n========== FLOWGUARD FAILURE TEST ==========")

    # Replace validation temporarily for this test only.
    orchestrator.validate_run = simulate_validation_failure

    try:
        orchestrator.run_pipeline()

    except RuntimeError as error:
        print("\nEXPECTED TEST FAILURE CAPTURED!")
        print(error)

    print("\nFailure test execution finished.")
    print("Now verify retries, skipped tasks and notification in MySQL.")


if __name__ == "__main__":
    main()
