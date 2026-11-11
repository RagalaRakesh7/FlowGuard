
import time

from app.orchestrator import execute_with_timeout, TaskTimeoutError


def simulate_slow_task(run_id):
    time.sleep(10)
    return {"accepted_count": 100}


if __name__ == "__main__":

    print("Testing FlowGuard task timeout...")

    try:
        execute_with_timeout(
            task_function=simulate_slow_task,
            run_id="TEST-RUN",
            timeout_seconds=3,
            task_name="TEST_TIMEOUT"
        )

        print("ERROR: Timeout was not triggered.")

    except TaskTimeoutError as error:
        print("\nTIMEOUT TEST SUCCESSFUL!")
        print(error)
