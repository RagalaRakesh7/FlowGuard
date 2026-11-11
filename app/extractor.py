
import csv
import json
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.db import get_connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "sample_orders.csv"

REQUIRED_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
    "order_status",
]


def parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def parse_amount(value):
    try:
        return Decimal(value) if value else None
    except InvalidOperation:
        return None


def extract_csv(source_path=DEFAULT_SOURCE):
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"CSV file not found: {source_path}")

    # Read and check the CSV before creating a pipeline run.
    with source_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header.")

        missing = [
            column for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing:
            raise ValueError(
                f"CSV is missing required columns: {missing}"
            )

        records = []

        # Start at 2 because line 1 contains the CSV header.
        for row_number, row in enumerate(reader, start=2):
            raw_payload = {
                key: value
                for key, value in row.items()
                if key is not None
            }

            records.append((
                row_number,
                raw_payload.get("order_id") or None,
                raw_payload.get("customer_id") or None,
                parse_date(raw_payload.get("order_date", "")),
                parse_amount(raw_payload.get("amount", "")),
                raw_payload.get("order_status") or None,
                json.dumps(raw_payload, ensure_ascii=False),
            ))

    run_id = str(uuid.uuid4())
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        # Register this pipeline run.
        cursor.execute(
            """
            INSERT INTO pipeline_runs
                (run_id, source_file, status, started_at, input_count)
            VALUES
                (%s, %s, 'RUNNING', NOW(), %s)
            """,
            (run_id, source_path.name, len(records)),
        )

        # Preserve all extracted source rows.
        if records:
            insert_sql = """
                INSERT INTO source_orders (
                    run_id,
                    source_file,
                    source_row_number,
                    order_id,
                    customer_id,
                    order_date,
                    amount,
                    order_status,
                    raw_payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = [
                (
                    run_id,
                    source_path.name,
                    row_number,
                    order_id,
                    customer_id,
                    order_date,
                    amount,
                    order_status,
                    raw_payload,
                )
                for (
                    row_number,
                    order_id,
                    customer_id,
                    order_date,
                    amount,
                    order_status,
                    raw_payload,
                ) in records
            ]

            cursor.executemany(insert_sql, values)

        connection.commit()

        return {
            "run_id": run_id,
            "source_file": source_path.name,
            "input_count": len(records),
            "status": "RUNNING",
        }

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    result = extract_csv()
    print("\nFLOWGUARD EXTRACTION SUCCESSFUL!")
    print("Run ID:", result["run_id"])
    print("Source:", result["source_file"])
    print("Extracted records:", result["input_count"])
    print("Status:", result["status"])
