from __future__ import annotations

import csv
import gzip
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from ranking_core import (
    rank_candidates,
    score_candidate,
    write_submission,
)


REFERENCE_DATE = date(2026, 6, 7)


def candidate(
    number: int,
    *,
    title: str = "Senior Machine Learning Engineer",
    summary: str = "Machine learning engineer with 7.0 years of production experience.",
    company: str = "ProductCo",
    industry: str = "Software",
    role_description: str | None = None,
    skills: list[dict] | None = None,
    years: float = 7.0,
    duration_months: int = 84,
) -> dict:
    description = role_description or (
        "Owned a hybrid BM25 and dense retrieval ranking pipeline in production. "
        "Designed NDCG evaluation and online A/B testing, then shipped the system to millions of users."
    )
    return {
        "candidate_id": f"CAND_{number:07d}",
        "profile": {
            "summary": summary,
            "location": "Pune, Maharashtra",
            "country": "India",
            "years_of_experience": years,
            "current_title": title,
            "current_company": company,
            "current_industry": industry,
        },
        "career_history": [
            {
                "company": company,
                "title": title,
                "start_date": "2019-06-01",
                "end_date": None,
                "duration_months": duration_months,
                "is_current": True,
                "industry": industry,
                "description": description,
            }
        ],
        "skills": skills
        or [
            {"name": "Python", "proficiency": "expert", "endorsements": 30, "duration_months": 72},
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 18, "duration_months": 36},
            {
                "name": "Learning to Rank",
                "proficiency": "advanced",
                "endorsements": 12,
                "duration_months": 30,
            },
        ],
        "redrob_signals": {
            "last_active_date": "2026-05-30",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.82,
            "notice_period_days": 30,
            "willing_to_relocate": True,
            "interview_completion_rate": 0.9,
            "applications_submitted_30d": 8,
            "saved_by_recruiters_30d": 12,
            "github_activity_score": 70,
            "verified_email": True,
            "verified_phone": True,
            "skill_assessment_scores": {"Python": 88},
        },
    }


class RankingTests(unittest.TestCase):
    def test_career_evidence_beats_keyword_stuffing(self) -> None:
        strong = score_candidate(candidate(1), REFERENCE_DATE)
        stuffer = candidate(
            2,
            title="Marketing Manager",
            summary="Marketing leader experimenting with AI tools.",
            industry="Consulting",
            role_description="Managed campaigns, budgets, and a content team.",
            skills=[
                {"name": "Embeddings", "proficiency": "expert", "endorsements": 60, "duration_months": 48},
                {"name": "Pinecone", "proficiency": "expert", "endorsements": 50, "duration_months": 42},
                {"name": "Learning to Rank", "proficiency": "expert", "endorsements": 55, "duration_months": 40},
            ],
        )
        weak = score_candidate(stuffer, REFERENCE_DATE)
        self.assertGreater(strong.score, weak.score + 50)

    def test_impossible_company_timeline_is_hard_penalized(self) -> None:
        trap = candidate(3, company="Sarvam AI")
        result = score_candidate(trap, REFERENCE_DATE)
        self.assertTrue(result.integrity_failures)
        self.assertLessEqual(result.score, 5.0)

    def test_submission_is_deterministic_and_limited_to_100(self) -> None:
        ranked = [score_candidate(candidate(i), REFERENCE_DATE) for i in range(1, 106)]
        ranked.sort(key=lambda item: (-round(item.score, 8), item.candidate_id))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "submission.csv"
            self.assertEqual(write_submission(ranked, output), 100)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 100)
        self.assertEqual([int(row["rank"]) for row in rows], list(range(1, 101)))
        self.assertEqual([row["candidate_id"] for row in rows], sorted(row["candidate_id"] for row in rows))
        self.assertTrue(all(rows[i]["score"] >= rows[i + 1]["score"] for i in range(99)))

    def test_json_array_input_and_reference_date_inference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "candidates.json"
            source.write_text(json.dumps([candidate(1), candidate(2)]), encoding="utf-8")
            ranked, inferred = rank_candidates(source)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(inferred, date(2026, 6, 6))

    def test_compressed_jsonl_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "candidates.jsonl.gz"
            with gzip.open(source, "wt", encoding="utf-8") as handle:
                handle.write(json.dumps(candidate(1)) + "\n")
                handle.write(json.dumps(candidate(2)) + "\n")
            ranked, _ = rank_candidates(source, REFERENCE_DATE)
        self.assertEqual([item.candidate_id for item in ranked], ["CAND_0000001", "CAND_0000002"])

    def test_duplicate_candidate_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "candidates.jsonl"
            source.write_text(
                json.dumps(candidate(1)) + "\n" + json.dumps(candidate(1)) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate candidate_id"):
                rank_candidates(source, REFERENCE_DATE)


if __name__ == "__main__":
    unittest.main()
