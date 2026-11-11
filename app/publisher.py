
from app.db import get_connection


def publish_run(run_id):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # 1. Confirm the pipeline run exists and is still running.
        cursor.execute(
            """
            SELECT
                status,
                input_count,
                accepted_count,
                rejected_count,
                transformed_count
            FROM pipeline_runs
            WHERE run_id = %s
            FOR UPDATE
            """,
            (run_id,),
        )

        run = cursor.fetchone()

        if not run:
            raise ValueError("Pipeline run does not exist.")

        status, input_count, accepted_count, rejected_count, transformed_count = run

        if status != "RUNNING":
            raise ValueError(f"Cannot publish a run with status {status}.")

        if None in (input_count, accepted_count, rejected_count, transformed_count):
            raise ValueError("Pipeline counts are incomplete.")

        if input_count != accepted_count + rejected_count:
            raise ValueError("Validation counts do not reconcile.")

        if transformed_count != accepted_count:
            raise ValueError("Transformed count does not match accepted count.")

        # 2. Independently verify the records in MySQL.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM source_orders
            WHERE run_id = %s
            """,
            (run_id,),
        )
        actual_source_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM rejected_records
            WHERE run_id = %s
            """,
            (run_id,),
        )
        actual_rejected_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM transformed_orders
            WHERE run_id = %s
            """,
            (run_id,),
        )
        actual_transformed_count = cursor.fetchone()[0]

        if actual_source_count != input_count:
            raise ValueError("Source record count does not match input count.")

        if actual_rejected_count != rejected_count:
            raise ValueError("Rejected record count does not match validation.")

        if actual_transformed_count != transformed_count:
            raise ValueError("Transformed record count does not match pipeline metrics.")

        # 3. Ensure no rejected source record is being published.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM transformed_orders t
            INNER JOIN rejected_records r
                ON t.source_record_id = r.source_record_id
               AND t.run_id = r.run_id
            WHERE t.run_id = %s
            """,
            (run_id,),
        )

        rejected_in_transformed = cursor.fetchone()[0]

        if rejected_in_transformed:
            raise ValueError("Rejected records found in transformed data.")

        # 4. Read clean records.
        cursor.execute(
            """
            SELECT
                order_id,
                customer_id,
                order_date,
                amount,
                order_status
            FROM transformed_orders
            WHERE run_id = %s
            ORDER BY transformed_id
            """,
            (run_id,),
        )

        records = cursor.fetchall()

        # 5. Publish with an idempotent upsert.
        # order_id is the unique business key.
        if records:
            publish_sql = """
                INSERT INTO published_orders (
                    order_id,
                    customer_id,
                    order_date,
                    amount,
                    order_status,
                    source_run_id,
                    published_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    customer_id = VALUES(customer_id),
                    order_date = VALUES(order_date),
                    amount = VALUES(amount),
                    order_status = VALUES(order_status),
                    source_run_id = VALUES(source_run_id),
                    published_at = NOW()
            """

            values = [
                (
                    order_id,
                    customer_id,
                    order_date,
                    amount,
                    order_status,
                    run_id,
                )
                for (
                    order_id,
                    customer_id,
                    order_date,
                    amount,
                    order_status,
                ) in records
            ]

            cursor.executemany(publish_sql, values)

        # 6. Update metrics and finish the run.
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET published_count = %s,
                status = 'SUCCEEDED',
                completed_at = NOW()
            WHERE run_id = %s
            """,
            (len(records), run_id),
        )

        connection.commit()

        return {
            "run_id": run_id,
            "published_count": len(records),
            "status": "SUCCEEDED",
        }

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if connection and connection.is_connected():
            connection.close()
