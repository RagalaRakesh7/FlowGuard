
from app.db import get_connection


def transform_run(run_id):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Select only records that passed validation.
        cursor.execute(
            """
            SELECT
                s.source_record_id,
                s.order_id,
                s.customer_id,
                s.order_date,
                s.amount,
                s.order_status
            FROM source_orders s
            LEFT JOIN rejected_records r
                ON s.source_record_id = r.source_record_id
                AND r.run_id = s.run_id
            WHERE s.run_id = %s
              AND r.reject_id IS NULL
            ORDER BY s.source_row_number ASC
            """,
            (run_id,),
        )

        records = cursor.fetchall()

        # Make reruns safe for this pipeline run.
        cursor.execute(
            """
            DELETE FROM transformed_orders
            WHERE run_id = %s
            """,
            (run_id,),
        )

        insert_sql = """
            INSERT INTO transformed_orders (
                run_id,
                source_record_id,
                order_id,
                customer_id,
                order_date,
                amount,
                order_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        transformed_records = []

        for record in records:
            (
                source_record_id,
                order_id,
                customer_id,
                order_date,
                amount,
                order_status,
            ) = record

            transformed_records.append((
                run_id,
                source_record_id,
                order_id.strip(),
                customer_id.strip(),
                order_date,
                amount,
                order_status.strip().upper(),
            ))

        if transformed_records:
            cursor.executemany(insert_sql, transformed_records)

        transformed_count = len(transformed_records)

        cursor.execute(
            """
            UPDATE pipeline_runs
            SET transformed_count = %s
            WHERE run_id = %s
            """,
            (transformed_count, run_id),
        )

        connection.commit()

        return {
            "run_id": run_id,
            "transformed_count": transformed_count,
        }

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    raise SystemExit(
        "Import transform_run(run_id) and call it with a validated run ID."
    )
