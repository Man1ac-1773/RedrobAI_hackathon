#!/usr/bin/env python3
"""Generate a Redrob submission CSV from a supplied candidate dataset."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ranking_core import load_feature_artifact, rank_candidates, write_submission


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank candidates for the Senior AI Engineer role")
    parser.add_argument("--candidates", required=True, help="Path to .jsonl, .jsonl.gz, .json, or .json.gz candidates")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument(
        "--features",
        help="Optional artifact made by offline_preprocess.py; it must match the candidate file exactly",
    )
    parser.add_argument(
        "--reference-date",
        help="Dataset snapshot date (YYYY-MM-DD). Default: infer from latest platform activity",
    )
    parser.add_argument("--limit", type=int, default=100, help="Rows to emit (default: 100)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        reference_date = None
        if args.reference_date:
            reference_date = datetime.strptime(args.reference_date, "%Y-%m-%d").date()

        if args.features:
            if reference_date is not None:
                raise ValueError("--reference-date cannot be combined with a precomputed --features artifact")
            ranked, resolved_date = load_feature_artifact(args.candidates, args.features)
            source = f"verified feature artifact {args.features}"
        else:
            ranked, resolved_date = rank_candidates(args.candidates, reference_date)
            source = "candidate records"

        written = write_submission(ranked, args.out, args.limit)
        print(
            f"Ranked {len(ranked):,} candidates from {source}; wrote {written} rows to {args.out} "
            f"(reference date {resolved_date.isoformat()})."
        )
        if written < args.limit:
            print(
                f"Warning: input contains only {written} candidates; official submissions require exactly 100 rows.",
                file=sys.stderr,
            )
        return 0
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Ranking failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
