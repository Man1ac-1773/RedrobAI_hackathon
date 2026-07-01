#!/usr/bin/env python3
"""Generate a compact, reproducible audit of the Redrob candidate pool."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ranking_core import infer_reference_date, integrity_failures, iter_candidates  # noqa: E402


TARGET_TITLES = {
    "AI Engineer",
    "Applied ML Engineer",
    "Lead AI Engineer",
    "Machine Learning Engineer",
    "NLP Engineer",
    "Recommendation Systems Engineer",
    "Search Engineer",
    "Senior AI Engineer",
    "Senior Applied Scientist",
    "Senior Machine Learning Engineer",
    "Senior NLP Engineer",
    "Staff Machine Learning Engineer",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the Redrob candidate dataset")
    parser.add_argument("--candidates", required=True, help="Candidate JSON/JSONL input")
    parser.add_argument("--out", default="EDA/EDA_report.md", help="Markdown report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reference_date, _ = infer_reference_date(args.candidates)
    titles: Counter[str] = Counter()
    industries: Counter[str] = Counter()
    failure_types: Counter[str] = Counter()
    integrity_candidates = 0
    target_profiles = 0
    low_availability = 0
    high_engagement = 0
    total = 0

    for candidate in iter_candidates(args.candidates):
        total += 1
        profile = candidate.get("profile", {})
        signals = candidate.get("redrob_signals", {})
        title = str(profile.get("current_title", "Unknown"))
        titles[title] += 1
        industries[str(profile.get("current_industry", "Unknown"))] += 1
        target_profiles += int(title in TARGET_TITLES)

        failures = integrity_failures(candidate)
        if failures:
            integrity_candidates += 1
            failure_types.update(failures)

        try:
            active_days = (reference_date - date.fromisoformat(signals["last_active_date"])).days
        except (KeyError, TypeError, ValueError):
            active_days = 3650
        response_rate = float(signals.get("recruiter_response_rate", 0.0) or 0.0)
        if active_days > 180 and response_rate < 0.10:
            low_availability += 1
        if active_days <= 90 and response_rate > 0.60:
            high_engagement += 1

    lines = [
        "# Candidate Dataset Audit",
        "",
        f"- Candidate records: **{total:,}**",
        f"- Dataset reference date inferred from activity: **{reference_date.isoformat()}**",
        f"- Direct target-role profiles: **{target_profiles:,}**",
        f"- Profiles failing at least one integrity check: **{integrity_candidates:,}**",
        "",
        "## Most Common Titles",
        "",
    ]
    lines.extend(f"- {title}: {count:,} ({count / total:.2%})" for title, count in titles.most_common(20))
    lines.extend(["", "## Most Common Industries", ""])
    lines.extend(f"- {industry}: {count:,} ({count / total:.2%})" for industry, count in industries.most_common(10))
    lines.extend(["", "## Integrity Findings", ""])
    lines.extend(f"- {reason}: {count:,}" for reason, count in failure_types.most_common())
    lines.extend(
        [
            "",
            "These checks are conservative consistency tests, not ground-truth labels. Any failing profile is held below score 5 by the ranker.",
            "",
            "## Behavioral Availability",
            "",
            f"- Inactive over 180 days with under 10% response: {low_availability:,}",
            f"- Active within 90 days with over 60% response: {high_engagement:,}",
            "",
            "The ranking uses behavior as a modifier after technical relevance; high engagement cannot rescue an irrelevant profile.",
            "",
        ]
    )

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote audit for {total:,} candidates to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
