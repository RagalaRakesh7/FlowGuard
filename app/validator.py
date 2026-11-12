
import json
from decimal import Decimal, InvalidOperation

from app.db import get_connection


VALID_STATUSES = {"PENDING", "PAID", "SHIPPED", "CANCELLED"}


def validate_run(run_id):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Fetch source records in a deterministic order.
        cursor.execute(
            """
            SELECT
                source_record_id,
                source_file,
                source_row_number,
                order_id,
                customer_id,
                order_date,
                amount,
                order_status,
                raw_payload
            FROM source_orders
            WHERE run_id = %s
            ORDER BY source_row_number ASC, source_record_id ASC
            """,
            (run_id,),
        )

        source_records = cursor.fetchall()

        # An empty batch is a valid, successful no-op. This keeps empty-input
        # runs observable instead of treating them as a pipeline failure.
        if not source_records:
            cursor.execute(
                """
                UPDATE pipeline_runs
                SET accepted_count = 0,
                    rejected_count = 0
                WHERE run_id = %s
                """,
                (run_id,),
            )
            connection.commit()

            return {
                "run_id": run_id,
                "input_count": 0,
                "accepted_count": 0,
                "rejected_count": 0,
            }

        accepted_count = 0
        rejected_count = 0
        seen_order_ids = set()
        rejection_rows = []

        for record in source_records:
            (
                source_record_id,
                source_file,
                row_number,
                order_id,
                customer_id,
                order_date,
                amount,
                order_status,
                raw_payload,
            ) = record

            reasons = []

            # Required business identifiers.
            clean_order_id = (
                order_id.strip() if order_id else ""
            )
            clean_customer_id = (
                customer_id.strip() if customer_id else ""
            )

            if not clean_order_id:
                reasons.append("Missing order ID")

            if not clean_customer_id:
                reasons.append("Missing customer ID")

            # Validate date.
            if order_date is None:
                reasons.append("Invalid or missing order date")

            # Validate amount.
            try:
                numeric_amount = Decimal(str(amount))
                if not numeric_amount.is_finite() or numeric_amount <= 0:
                    reasons.append("Amount must be greater than zero")
            except (InvalidOperation, TypeError, ValueError):
                reasons.append("Invalid or missing amount")

            # Validate order status.
            clean_status = (
                order_status.strip().upper()
                if order_status else ""
            )

            if clean_status not in VALID_STATUSES:
                reasons.append("Invalid or missing order status")

            # Detect duplicate business IDs.
            if clean_order_id:
                duplicate_key = clean_order_id

                if duplicate_key in seen_order_ids:
                    reasons.append("Duplicate order ID in this run")
                else:
                    seen_order_ids.add(duplicate_key)

            # Preserve the original payload.
            if isinstance(raw_payload, (dict, list)):
                payload_json = json.dumps(raw_payload)
            elif isinstance(raw_payload, str):
                payload_json = raw_payload
            else:
                payload_json = json.dumps(raw_payload, default=str)

            if reasons:
                rejected_count += 1

                rejection_rows.append((
                    run_id,
                    source_record_id,
                    source_file,
                    row_number,
                    clean_order_id or None,
                    "; ".join(reasons),
                    payload_json,
                ))
            else:
                accepted_count += 1

        # Make validation reruns safe for this run.
        cursor.execute(
            "DELETE FROM rejected_records WHERE run_id = %s",
            (run_id,),
        )

        if rejection_rows:
            cursor.executemany(
                """
                INSERT INTO rejected_records (
                    run_id,
                    source_record_id,
                    source_file,
                    source_row_number,
                    order_id,
                    rejection_reason,
                    raw_payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rejection_rows,
            )

        cursor.execute(
            """
            UPDATE pipeline_runs
            SET accepted_count = %s,
                rejected_count = %s
            WHERE run_id = %s
            """,
            (accepted_count, rejected_count, run_id),
        )

        connection.commit()

        return {
            "run_id": run_id,
            "input_count": len(source_records),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
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
        "Import validate_run(run_id) and call it with an existing pipeline run ID."
    )
