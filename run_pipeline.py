import argparse
import sys
from pathlib import Path

from app.orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run the FlowGuard data pipeline."
    )
    parser.add_argument(
        "source_path",
        nargs="?",
        default=None,
        help="Optional path to a CSV file. Defaults to data/sample_orders.csv.",
    )
    args = parser.parse_args()

    source_path = args.source_path
    if source_path is not None:
        source_path = Path(source_path)
        if not source_path.exists():
            parser.error(f"CSV file not found: {source_path}")

    try:
        result = run_pipeline(source_path)
        print("\nFINAL PIPELINE RESULT:")
        print(result)
        return 0
    except Exception:
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
