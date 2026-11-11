
import time
import traceback
import multiprocessing

from app.db import get_connection
from app.extractor import extract_csv
from app.validator import validate_run
from app.transformer import transform_run
from app.publisher import publish_run


# ==========================================
# CONFIGURATION
# ==========================================

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2

TASK_TIMEOUTS = {
    "VALIDATE": 60,
    "TRANSFORM": 60,
    "PUBLISH": 90,
}


class TaskTimeoutError(Exception):
    pass


class TaskExecutionError(Exception):
    pass


# ==========================================
# CONNECTION MANAGEMENT
# ==========================================

def close_connection(connection):
    if connection and connection.is_connected():
        connection.close()


# ==========================================
# CHILD PROCESS WORKER
# Must remain at module level for Windows spawn.
# ==========================================

def task_worker(task_function, run_id, send_connection):
    try:
        result = task_function(run_id)
        send_connection.send(("SUCCESS", result))

    except BaseException as error:
        send_connection.send((
            "FAILED",
            f"{type(error).__name__}: {error}"
        ))

    finally:
        send_connection.close()


# ==========================================
# PROCESS-LEVEL TASK EXECUTION
# ==========================================

def execute_with_timeout(
    task_function,
    run_id,
    timeout_seconds,
    task_name
):
    context = multiprocessing.get_context("spawn")

    receive_connection, send_connection = context.Pipe(
        duplex=False
    )

    process = context.Process(
        target=task_worker,
        args=(
            task_function,
            run_id,
            send_connection
        ),
        name=f"FlowGuard-{task_name}"
    )

    try:
        process.start()
        send_connection.close()

        # Wait for a result up to the configured timeout.
        if receive_connection.poll(timeout_seconds):
            try:
                message_type, payload = receive_connection.recv()
            except EOFError:
                message_type = "FAILED"
                payload = "Worker exited without returning a result."

            process.join(timeout=2)

            if process.is_alive():
                process.terminate()
                process.join()

            if message_type == "SUCCESS":
                return payload

            raise TaskExecutionError(payload)

        # No result within the time limit.
        if process.is_alive():
            process.terminate()
            process.join(timeout=3)

            if process.is_alive():
                process.kill()
                process.join()

        raise TaskTimeoutError(
            f"{task_name} exceeded its "
            f"{timeout_seconds}-second timeout."
        )

    finally:
        if process.is_alive():
            process.terminate()
            process.join()

        receive_connection.close()

        try:
            send_connection.close()
        except Exception:
            pass


# ==========================================
# TASK HISTORY
# ==========================================

def record_task_start(
    run_id,
    task_name,
    attempt_number,
    input_count=0
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO task_runs (
                run_id,
                task_name,
                attempt_number,
                status,
                started_at,
                input_count
            )
            VALUES (%s, %s, %s, 'RUNNING', NOW(), %s)
            """,
            (
                run_id,
                task_name,
                attempt_number,
                input_count
            )
        )

        task_run_id = cursor.lastrowid
        connection.commit()

        return task_run_id

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        close_connection(connection)


def record_task_end(
    task_run_id,
    status,
    output_count=0,
    error_message=None
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE task_runs
            SET
                status = %s,
                output_count = %s,
                error_message = %s,
                ended_at = NOW()
            WHERE task_run_id = %s
            """,
            (
                status,
                output_count,
                error_message[:2000] if error_message else None,
                task_run_id
            )
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        close_connection(connection)


# ==========================================
# NOTIFICATIONS
# ==========================================

def create_failure_notification(
    run_id,
    task_name,
    error_message
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        message = (
            f"Task {task_name} failed after "
            f"{MAX_ATTEMPTS} attempts. "
            f"Reason: {error_message[:1500]}"
        )

        cursor.execute(
            """
            INSERT INTO notifications (
                run_id,
                notification_type,
                message,
                is_read,
                created_at
            )
            VALUES (%s, 'FAILURE', %s, 0, NOW())
            """,
            (run_id, message)
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        close_connection(connection)


# ==========================================
# PIPELINE STATUS
# ==========================================

def update_pipeline_failure(run_id, error_message):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE pipeline_runs
            SET
                status = 'FAILED',
                error_message = %s,
                completed_at = NOW()
            WHERE run_id = %s
            """,
            (
                error_message[:2000],
                run_id
            )
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        close_connection(connection)


# ==========================================
# MARK DOWNSTREAM TASK AS SKIPPED
# ==========================================

def mark_task_skipped(
    run_id,
    task_name,
    input_count=0
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO task_runs (
                run_id,
                task_name,
                attempt_number,
                status,
                started_at,
                ended_at,
                input_count,
                output_count,
                error_message
            )
            VALUES (
                %s, %s, 0, 'SKIPPED',
                NOW(), NOW(), %s, 0,
                %s
            )
            """,
            (
                run_id,
                task_name,
                input_count,
                "Skipped because an upstream task failed."
            )
        )

        connection.commit()

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        close_connection(connection)


# ==========================================
# TASK EXECUTION WITH RETRIES AND TIMEOUTS
# ==========================================

def run_logged_task(
    run_id,
    task_name,
    task_function,
    input_count,
    output_key
):
    last_error = None

    timeout_seconds = TASK_TIMEOUTS[task_name]

    for attempt in range(1, MAX_ATTEMPTS + 1):

        task_run_id = record_task_start(
            run_id,
            task_name,
            attempt,
            input_count
        )

        start_time = time.perf_counter()

        try:
            print(
                f"\n[{task_name}] "
                f"Attempt {attempt}/{MAX_ATTEMPTS}"
            )

            print(
                f"[{task_name}] Timeout: "
                f"{timeout_seconds} seconds"
            )

            result = execute_with_timeout(
                task_function=task_function,
                run_id=run_id,
                timeout_seconds=timeout_seconds,
                task_name=task_name
            )

            duration = time.perf_counter() - start_time

            output_count = result[output_key]

            record_task_end(
                task_run_id,
                "SUCCEEDED",
                output_count
            )

            print(
                f"[{task_name}] SUCCESS | "
                f"Output: {output_count} | "
                f"Duration: {duration:.2f} seconds"
            )

            return result

        except TaskTimeoutError as error:

            last_error = str(error)

            record_task_end(
                task_run_id,
                "TIMED_OUT",
                error_message=last_error
            )

            print(
                f"[{task_name}] TIMED OUT | "
                f"{last_error}"
            )

        except Exception as error:

            last_error = str(error)

            record_task_end(
                task_run_id,
                "FAILED",
                error_message=last_error
            )

            print(
                f"[{task_name}] FAILED | "
                f"{last_error}"
            )

        if attempt < MAX_ATTEMPTS:

            print(
                f"Retrying {task_name} in "
                f"{RETRY_DELAY_SECONDS} seconds..."
            )

            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"{task_name} failed after {MAX_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )


# ==========================================
# MAIN PIPELINE
# ==========================================

def run_pipeline(source_path=None):

    print("\n")
    print("=" * 55)
    print("       FLOWGUARD PIPELINE ORCHESTRATOR")
    print("=" * 55)

    run_id = None
    input_count = 0

    validation = None
    transformation = None

    current_task = "EXTRACT"

    try:

        # ----------------------------------
        # TASK 1: EXTRACT
        # ----------------------------------

        print("\n[EXTRACT] Starting extraction...")

        if source_path is None:
            extraction = extract_csv()
        else:
            extraction = extract_csv(source_path)

        run_id = extraction["run_id"]
        input_count = extraction["input_count"]

        print("\nPipeline Run ID:", run_id)

        extract_task_id = record_task_start(
            run_id,
            "EXTRACT",
            1,
            0
        )

        record_task_end(
            extract_task_id,
            "SUCCEEDED",
            input_count
        )

        print(
            f"[EXTRACT] SUCCESS | "
            f"Records: {input_count}"
        )

        # ----------------------------------
        # TASK 2: VALIDATE
        # ----------------------------------

        current_task = "VALIDATE"

        validation = run_logged_task(
            run_id=run_id,
            task_name="VALIDATE",
            task_function=validate_run,
            input_count=input_count,
            output_key="accepted_count"
        )

        accepted_count = validation["accepted_count"]
        rejected_count = validation["rejected_count"]

        # ----------------------------------
        # TASK 3: TRANSFORM
        # ----------------------------------

        current_task = "TRANSFORM"

        transformation = run_logged_task(
            run_id=run_id,
            task_name="TRANSFORM",
            task_function=transform_run,
            input_count=accepted_count,
            output_key="transformed_count"
        )

        transformed_count = transformation["transformed_count"]

        # ----------------------------------
        # TASK 4: PUBLISH
        # ----------------------------------

        current_task = "PUBLISH"

        publishing = run_logged_task(
            run_id=run_id,
            task_name="PUBLISH",
            task_function=publish_run,
            input_count=transformed_count,
            output_key="published_count"
        )

        published_count = publishing["published_count"]

        # ----------------------------------
        # SUCCESS SUMMARY
        # ----------------------------------

        print("\n")
        print("=" * 55)
        print("       FLOWGUARD PIPELINE SUCCEEDED")
        print("=" * 55)

        print("Run ID:", run_id)
        print("Input Records:", input_count)
        print("Accepted Records:", accepted_count)
        print("Rejected Records:", rejected_count)
        print("Transformed Records:", transformed_count)
        print("Published Records:", published_count)

        return {
            "run_id": run_id,
            "status": "SUCCEEDED",
            "input_count": input_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "transformed_count": transformed_count,
            "published_count": published_count
        }

    except Exception as error:

        print("\n")
        print("=" * 55)
        print("       FLOWGUARD PIPELINE FAILED")
        print("=" * 55)

        print("Failed Task:", current_task)
        print("Error:", error)

        # Define only the tasks downstream of the failed task.
        downstream_tasks = {
            "EXTRACT": ["VALIDATE", "TRANSFORM", "PUBLISH"],
            "VALIDATE": ["TRANSFORM", "PUBLISH"],
            "TRANSFORM": ["PUBLISH"],
            "PUBLISH": []
        }

        skip_counts = {
            "VALIDATE": input_count,
            "TRANSFORM": (
                validation["accepted_count"] if validation else 0
            ),
            "PUBLISH": (
                transformation["transformed_count"]
                if transformation else 0
            )
        }

        if run_id:

            # Block downstream execution.
            for task_name in downstream_tasks[current_task]:

                try:
                    mark_task_skipped(
                        run_id,
                        task_name,
                        skip_counts.get(task_name, 0)
                    )

                    print(
                        f"[{task_name}] SKIPPED - "
                        "Upstream task failed."
                    )

                except Exception as skip_error:

                    print(
                        f"Could not skip {task_name}: "
                        f"{skip_error}"
                    )

            # Create one failure notification.
            try:
                create_failure_notification(
                    run_id,
                    current_task,
                    str(error)
                )

            except Exception as notification_error:

                print(
                    "Notification error:",
                    notification_error
                )

            # Mark pipeline failed.
            try:
                update_pipeline_failure(
                    run_id,
                    str(error)
                )

            except Exception as status_error:

                print(
                    "Pipeline status update error:",
                    status_error
                )

        print("\nPipeline execution stopped.")

        raise


# ==========================================
# DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    try:
        result = run_pipeline()

        print("\nFINAL PIPELINE RESULT:")
        print(result)

    except Exception:
        traceback.print_exc()
