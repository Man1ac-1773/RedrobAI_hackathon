#!/usr/bin/env python3
"""Build an optional, dataset-bound feature artifact for faster reproduction."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ranking_core import write_feature_artifact


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Precompute deterministic Redrob ranking features")
    parser.add_argument("--candidates", required=True, help="Source candidate dataset")
    parser.add_argument("--out", required=True, help="Artifact path; use .gz for compression")
    parser.add_argument(
        "--reference-date",
        help="Dataset snapshot date (YYYY-MM-DD). Default: infer from latest platform activity",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        reference_date = (
            datetime.strptime(args.reference_date, "%Y-%m-%d").date() if args.reference_date else None
        )
        count, resolved_date = write_feature_artifact(args.candidates, args.out, reference_date)
        print(
            f"Wrote {count:,} scored candidate records to {args.out} "
            f"(reference date {resolved_date.isoformat()})."
        )
        return 0
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Preprocessing failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
