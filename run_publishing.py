
from app.db import get_connection
from app.publisher import publish_run


def main():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT run_id
            FROM pipeline_runs
            WHERE status = 'RUNNING'
              AND transformed_count IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """
        )

        result = cursor.fetchone()
        cursor.close()

    finally:
        connection.close()

    if not result:
        raise RuntimeError("No transformed RUNNING pipeline run found.")

    run_id = result[0]

    print("Publishing run:", run_id)

    summary = publish_run(run_id)

    print("\nFLOWGUARD PUBLISHING SUCCESSFUL!")
    print("Published records:", summary["published_count"])
    print("Final status:", summary["status"])


if __name__ == "__main__":
    main()
