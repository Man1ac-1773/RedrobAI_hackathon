#!/usr/bin/env python3
"""Run submission-critical checks against a supplied candidate dataset."""

from __future__ import annotations

import argparse
import ast
import csv
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from ranking_core import OUTPUT_COLUMNS, integrity_failures, iter_candidates


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = (
    "README.md",
    "rank.py",
    "ranking_core.py",
    "pyproject.toml",
    "uv.lock",
    "submission_metadata.yaml",
    "demo.ipynb",
    "sample_candidates.json",
    "docs/TECHNICAL_APPROACH.md",
    "docs/SUBMISSION_CHECKLIST.md",
    "tests/test_ranking.py",
)
FORBIDDEN_RANKING_IMPORTS = {
    "anthropic",
    "cohere",
    "google.generativeai",
    "httpx",
    "numpy",
    "openai",
    "pandas",
    "requests",
    "sentence_transformers",
    "socket",
    "torch",
    "urllib",
}


class CheckFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def check_repository() -> list[str]:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    require(not missing, f"missing required repository files: {', '.join(missing)}")

    imported = imported_modules(ROOT / "rank.py") | imported_modules(ROOT / "ranking_core.py")
    forbidden = sorted(
        module for module in imported if any(module == item or module.startswith(item + ".") for item in FORBIDDEN_RANKING_IMPORTS)
    )
    require(not forbidden, f"ranking path imports forbidden network/heavy modules: {', '.join(forbidden)}")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    require("dependencies = []" in pyproject, "direct ranker must retain an empty dependency list")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    command = "python3 rank.py --candidates ./candidates.jsonl --out ./submission.csv"
    require(command in readme, "README is missing the exact reproduction command")

    metadata = (ROOT / "submission_metadata.yaml").read_text(encoding="utf-8")
    require(f'reproduce_command: "{command}"' in metadata, "metadata reproduction command differs from README")
    require("uses_gpu_for_inference: false" in metadata, "metadata must declare CPU-only inference")
    require("has_network_during_ranking: false" in metadata, "metadata must declare network-off ranking")
    require("pre_computation_required: false" in metadata, "metadata must match the direct ranking path")
    require("colab.research.google.com/github/" in metadata, "metadata must contain a repository-backed Colab URL")
    return [
        "required repository files are present",
        "ranking path has no forbidden network/heavy imports",
        "README, dependency declaration, and metadata contract agree",
    ]


def load_source_candidates(
    path: Path, selected_ids: set[str]
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    ids: set[str] = set()
    records: dict[str, dict[str, Any]] = {}
    for candidate in iter_candidates(path):
        candidate_id = str(candidate.get("candidate_id", ""))
        require(candidate_id not in ids, f"duplicate candidate ID in source: {candidate_id}")
        ids.add(candidate_id)
        if candidate_id in selected_ids:
            records[candidate_id] = candidate
    require(bool(ids), "candidate source is empty")
    return ids, records


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames or ()) == OUTPUT_COLUMNS, f"CSV header must be {','.join(OUTPUT_COLUMNS)}")
        return list(reader)


def check_output(
    rows: list[dict[str, str]],
    source_ids: set[str],
    source_records: dict[str, dict[str, Any]],
) -> list[str]:
    expected = min(100, len(source_ids))
    require(len(rows) == expected, f"expected {expected} output rows, found {len(rows)}")

    output_ids = [row["candidate_id"].strip() for row in rows]
    require(len(set(output_ids)) == len(output_ids), "output contains duplicate candidate IDs")
    require(set(output_ids) <= source_ids, "output contains candidate IDs absent from the supplied source")

    ranks: list[int] = []
    scores: list[float] = []
    reasoning: list[str] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            rank = int(row["rank"])
            score = float(row["score"])
        except ValueError as exc:
            raise CheckFailure(f"row {row_number} has a non-numeric rank or score") from exc
        require(math.isfinite(score), f"row {row_number} score is not finite")
        ranks.append(rank)
        scores.append(score)
        reasoning.append(row["reasoning"].strip())

    require(ranks == list(range(1, expected + 1)), "ranks are not contiguous and ordered")
    require(all(scores[index] >= scores[index + 1] for index in range(len(scores) - 1)), "scores increase with rank")
    for index in range(len(scores) - 1):
        if scores[index] == scores[index + 1]:
            require(output_ids[index] < output_ids[index + 1], "equal-score tie is not candidate-ID ascending")

    require(all(reasoning), "one or more reasoning fields are empty")
    uniqueness = len(set(reasoning)) / len(reasoning)
    require(uniqueness >= 0.90, f"reasoning uniqueness is too low: {uniqueness:.1%}")

    integrity_count = sum(bool(integrity_failures(source_records[candidate_id])) for candidate_id in output_ids)
    require(integrity_count == 0, f"top output contains {integrity_count} integrity-failing profiles")

    grounded = 0
    for candidate_id, explanation in zip(output_ids, reasoning):
        profile = source_records[candidate_id].get("profile", {})
        title = str(profile.get("current_title", "")).strip()
        company = str(profile.get("current_company", "")).strip()
        grounded += int(bool(title and company and title in explanation and company in explanation))
    require(grounded == len(rows), f"only {grounded}/{len(rows)} explanations include the source title and company")

    return [
        f"CSV structure and ordering are valid ({len(rows)} rows)",
        "all output IDs exist in the supplied candidate pool",
        f"reasoning is non-empty, grounded, and {uniqueness:.0%} unique",
        "no selected candidate fails an integrity check",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Redrob submission preflight checks")
    parser.add_argument("--candidates", required=True, help="Candidate JSON/JSONL input")
    parser.add_argument("--out", help="Keep the generated CSV at this path; otherwise use a temporary file")
    parser.add_argument("--timeout", type=float, default=300.0, help="Maximum ranking seconds (default: 300)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = Path(args.candidates).resolve()
    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        messages = check_repository()
        if args.out:
            output = Path(args.out).resolve()
        else:
            temporary = tempfile.TemporaryDirectory(prefix="redrob-preflight-")
            output = Path(temporary.name) / "submission.csv"

        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, str(ROOT / "rank.py"), "--candidates", str(candidates), "--out", str(output)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=args.timeout,
            check=False,
        )
        elapsed = time.perf_counter() - started
        require(completed.returncode == 0, f"ranking command failed:\n{completed.stderr or completed.stdout}")
        require(elapsed <= args.timeout, f"ranking exceeded {args.timeout:.1f} seconds")
        rows = load_csv(output)
        selected_ids = {row["candidate_id"].strip() for row in rows}
        source_ids, source_records = load_source_candidates(candidates, selected_ids)
        messages.extend(check_output(rows, source_ids, source_records))
        messages.append(f"ranking completed in {elapsed:.2f}s (limit {args.timeout:.0f}s)")

        print("Submission preflight: PASS")
        for message in messages:
            print(f"[PASS] {message}")
        if args.out:
            print(f"[PASS] retained generated CSV at {output}")
        return 0
    except (CheckFailure, FileNotFoundError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"Submission preflight: FAIL\n[FAIL] {exc}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
