
from app.db import get_connection
from app.transformer import transform_run


def main():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT run_id
            FROM pipeline_runs
            WHERE status = 'RUNNING'
              AND accepted_count IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """
        )

        result = cursor.fetchone()
        cursor.close()

    finally:
        connection.close()

    if not result:
        raise RuntimeError(
            "No validated RUNNING pipeline run found."
        )

    run_id = result[0]

    print("Transforming run:", run_id)

    summary = transform_run(run_id)

    print("\nFLOWGUARD TRANSFORMATION SUCCESSFUL!")
    print("Transformed records:", summary["transformed_count"])


if __name__ == "__main__":
    main()
