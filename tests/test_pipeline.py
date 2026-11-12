import csv
from pathlib import Path

import pytest

from app.extractor import extract_csv
from app.orchestrator import run_pipeline, TaskExecutionError, TaskTimeoutError


def write_csv(path: Path, rows, fieldnames=None):
    fieldnames = fieldnames or [
        "order_id",
        "customer_id",
        "order_date",
        "amount",
        "order_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def valid_rows(count=5, prefix="T"):
    rows = []
    for i in range(1, count + 1):
        rows.append(
            {
                "order_id": f"{prefix}-{i:03d}",
                "customer_id": f"CUST-{i:03d}",
                "order_date": "2026-01-15",
                "amount": "100.50",
                "order_status": "PAID",
            }
        )
    return rows


def test_unexpected_schema_raises(tmp_path):
    csv_path = tmp_path / "bad_schema.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["foo", "bar"])
        writer.writeheader()
        writer.writerow({"foo": "1", "bar": "2"})

    with pytest.raises(ValueError, match="missing required columns"):
        extract_csv(csv_path)


def test_extract_missing_file_raises(tmp_path):
    missing = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        extract_csv(missing)


def test_happy_path_pipeline(tmp_path):
    csv_path = tmp_path / "happy.csv"
    write_csv(csv_path, valid_rows(5, "HAPPY"))

    result = run_pipeline(csv_path)

    assert result["status"] == "SUCCEEDED"
    assert result["input_count"] == 5
    assert result["accepted_count"] == 5
    assert result["rejected_count"] == 0
    assert result["transformed_count"] == 5
    assert result["published_count"] == 5


def test_empty_input_pipeline(tmp_path):
    csv_path = tmp_path / "empty.csv"
    write_csv(csv_path, [])

    result = run_pipeline(csv_path)

    assert result["status"] == "SUCCEEDED"
    assert result["input_count"] == 0
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 0
    assert result["transformed_count"] == 0
    assert result["published_count"] == 0


def test_malformed_records_are_rejected(tmp_path):
    rows = [
        {
            "order_id": "BAD-1",
            "customer_id": "CUST-1",
            "order_date": "not-a-date",
            "amount": "100.00",
            "order_status": "PAID",
        },
        {
            "order_id": "BAD-2",
            "customer_id": "CUST-2",
            "order_date": "2026-01-15",
            "amount": "-10",
            "order_status": "PAID",
        },
        {
            "order_id": "BAD-3",
            "customer_id": "CUST-3",
            "order_date": "2026-01-15",
            "amount": "100.00",
            "order_status": "UNKNOWN",
        },
        {
            "order_id": "BAD-4",
            "customer_id": "",
            "order_date": "2026-01-15",
            "amount": "100.00",
            "order_status": "PAID",
        },
        {
            "order_id": "BAD-5",
            "customer_id": "CUST-5",
            "order_date": "2026-01-15",
            "amount": "100.00",
            "order_status": "PAID",
        },
    ]
    # Duplicate business key.
    rows[4]["order_id"] = rows[0]["order_id"]

    csv_path = tmp_path / "malformed.csv"
    write_csv(csv_path, rows)

    result = run_pipeline(csv_path)

    assert result["status"] == "SUCCEEDED"
    assert result["input_count"] == 5
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 5
    assert result["transformed_count"] == 0
    assert result["published_count"] == 0


def test_null_values_are_rejected(tmp_path):
    rows = [
        {
            "order_id": "",
            "customer_id": "",
            "order_date": "",
            "amount": "",
            "order_status": "",
        }
    ]
    csv_path = tmp_path / "nulls.csv"
    write_csv(csv_path, rows)

    result = run_pipeline(csv_path)

    assert result["status"] == "SUCCEEDED"
    assert result["input_count"] == 1
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 1


def test_rerun_does_not_duplicate_published_orders(tmp_path):
    csv_path = tmp_path / "rerun.csv"
    write_csv(csv_path, valid_rows(3, "RERUN"))

    first = run_pipeline(csv_path)
    second = run_pipeline(csv_path)

    assert first["status"] == "SUCCEEDED"
    assert second["status"] == "SUCCEEDED"
    assert second["published_count"] == 3


def failing_validator(run_id):
    raise RuntimeError("Simulated validation failure")


def test_upstream_failure_prevents_publish(tmp_path, monkeypatch):
    import app.orchestrator as orchestrator

    monkeypatch.setattr(orchestrator, "validate_run", failing_validator)

    csv_path = tmp_path / "failure.csv"
    write_csv(csv_path, valid_rows(2, "FAIL"))

    with pytest.raises(RuntimeError):
        run_pipeline(csv_path)
