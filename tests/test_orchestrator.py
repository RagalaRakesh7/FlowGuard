
import time
import pytest

from app.orchestrator import (
    execute_with_timeout,
    TaskTimeoutError,
    TaskExecutionError,
)


# ==========================================
# TEST WORKER FUNCTIONS
# Keep these at module level for Windows.
# ==========================================

def successful_task(run_id):
    return {
        "run_id": run_id,
        "accepted_count": 100
    }


def slow_task(run_id):
    time.sleep(10)

    return {
        "run_id": run_id,
        "accepted_count": 100
    }


def failing_task(run_id):
    raise ValueError("Simulated task failure")


# ==========================================
# TEST 1: SUCCESSFUL TASK
# ==========================================

def test_successful_task_execution():

    result = execute_with_timeout(
        task_function=successful_task,
        run_id="TEST-001",
        timeout_seconds=5,
        task_name="TEST_SUCCESS"
    )

    assert result["run_id"] == "TEST-001"
    assert result["accepted_count"] == 100


# ==========================================
# TEST 2: TASK TIMEOUT
# ==========================================

def test_task_timeout():

    with pytest.raises(TaskTimeoutError):

        execute_with_timeout(
            task_function=slow_task,
            run_id="TEST-002",
            timeout_seconds=2,
            task_name="TEST_TIMEOUT"
        )


# ==========================================
# TEST 3: TASK FAILURE
# ==========================================

def test_task_failure():

    with pytest.raises(TaskExecutionError):

        execute_with_timeout(
            task_function=failing_task,
            run_id="TEST-003",
            timeout_seconds=5,
            task_name="TEST_FAILURE"
        )


# ==========================================
# TEST 4: RESULT STRUCTURE
# ==========================================

def test_successful_result_structure():

    result = execute_with_timeout(
        task_function=successful_task,
        run_id="TEST-004",
        timeout_seconds=5,
        task_name="TEST_RESULT"
    )

    assert isinstance(result, dict)
    assert "run_id" in result
    assert "accepted_count" in result
