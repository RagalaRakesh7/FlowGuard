
import csv
import random
import argparse
from pathlib import Path
from datetime import date, timedelta


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "sample_orders.csv"

COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "amount",
    "order_status"
]


def generate_orders(row_count=100):
    random_generator = random.Random(42)
    rows = []

    statuses = ["PENDING", "PAID", "SHIPPED", "CANCELLED"]

    for i in range(1, row_count + 1):
        order_date = date(2026, 1, 1) + timedelta(
            days=random_generator.randint(0, 300)
        )

        row = {
            "order_id": f"ORD-{i:05d}",
            "customer_id": f"CUST-{random_generator.randint(1, 50):04d}",
            "order_date": order_date.isoformat(),
            "amount": round(random_generator.uniform(100, 10000), 2),
            "order_status": random_generator.choice(statuses)
        }

        rows.append(row)

    # Inject data-quality issues when enough rows exist.
    if row_count >= 5:
        rows[0]["amount"] = "-500"
        rows[1]["customer_id"] = ""
        rows[2]["order_date"] = "invalid-date"
        rows[3]["order_status"] = "UNKNOWN"

        # Duplicate the first order's business ID.
        rows[4]["order_id"] = rows[0]["order_id"]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print("FLOWGUARD DATA GENERATION SUCCESSFUL!")
    print(f"Records generated: {len(rows)}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100)
    args = parser.parse_args()

    if args.rows < 1:
        parser.error("--rows must be at least 1")

    generate_orders(args.rows)
