
from app.db import get_connection
from app.validator import validate_run


def main():
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT run_id
            FROM pipeline_runs
            WHERE status = 'RUNNING'
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
        result = cursor.fetchone()
        cursor.close()

    finally:
        connection.close()

    if not result:
        raise RuntimeError("No RUNNING pipeline run found.")

    run_id = result[0]
    print("Validating run:", run_id)

    summary = validate_run(run_id)

    print("\nFLOWGUARD VALIDATION SUCCESSFUL!")
    print("Input records:", summary["input_count"])
    print("Accepted records:", summary["accepted_count"])
    print("Rejected records:", summary["rejected_count"])


if __name__ == "__main__":
    main()
