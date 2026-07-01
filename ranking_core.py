"""Deterministic, CPU-only candidate ranking for the Redrob challenge.

The scorer deliberately gives career evidence more weight than self-declared
skills.  This is both harder to game and closer to the job description, which
asks for production retrieval/ranking ownership rather than keyword coverage.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any, Iterator


OUTPUT_COLUMNS = ("candidate_id", "rank", "score", "reasoning")
CANDIDATE_ID_RE = re.compile(r"^CAND_[0-9]{7}$")
YEARS_RE = re.compile(r"\b(\d{1,2}(?:\.\d+)?)\+?\s+years?\b", re.IGNORECASE)

PROFICIENCY = {"beginner": 0.20, "intermediate": 0.48, "advanced": 0.78, "expert": 1.0}

# Conservative founding years used only for impossible-date detection.  These
# four companies account for the explicit "company younger than tenure" trap in
# the released data.  A start in the founding year is accepted.
COMPANY_FOUNDING_YEAR = {
    "glance": 2019,
    "krutrim": 2023,
    "rephrase.ai": 2019,
    "sarvam ai": 2023,
}

CONSULTING_COMPANIES = {
    "accenture",
    "capgemini",
    "cognizant",
    "genpact",
    "genpact ai",
    "hcl",
    "hcl technologies",
    "infosys",
    "mindtree",
    "mphasis",
    "tata consultancy services",
    "tcs",
    "tech mahindra",
    "wipro",
}

PRODUCT_COMPANIES = {
    "adobe",
    "amazon",
    "apple",
    "cred",
    "dream11",
    "flipkart",
    "freshworks",
    "glance",
    "google",
    "haptik",
    "inmobi",
    "linkedin",
    "meesho",
    "meta",
    "microsoft",
    "netflix",
    "nykaa",
    "ola",
    "paytm",
    "phonepe",
    "policybazaar",
    "razorpay",
    "salesforce",
    "swiggy",
    "unacademy",
    "uber",
    "vedantu",
    "zomato",
    "zoho",
}

PRODUCT_INDUSTRIES = {
    "e-commerce",
    "edtech",
    "fintech",
    "food delivery",
    "hr tech",
    "internet",
    "marketplace",
    "product",
    "saas",
    "software",
}

PREFERRED_CITIES = {"pune", "noida", "delhi", "gurgaon", "gurugram", "mumbai", "hyderabad"}
INDIA_COUNTRY_NAMES = {"india", "in"}

NON_TECH_TITLE_TERMS = {
    "accountant",
    "civil engineer",
    "content writer",
    "customer support",
    "graphic designer",
    "hr manager",
    "marketing manager",
    "mechanical engineer",
    "operations manager",
    "sales executive",
}

TECHNICAL_TITLE_TERMS = {
    "ai",
    "backend",
    "data",
    "developer",
    "engineer",
    "machine learning",
    "ml",
    "nlp",
    "scientist",
    "search",
    "software",
}

SKILL_GROUPS = {
    "python": {"python"},
    "retrieval": {
        "bm25",
        "content matching",
        "embeddings",
        "information retrieval",
        "information retrieval systems",
        "natural language processing",
        "nlp",
        "search & discovery",
        "semantic search",
        "sentence transformers",
        "text encoders",
        "vector representations",
        "vector search",
    },
    "vector_infra": {
        "elasticsearch",
        "faiss",
        "milvus",
        "opensearch",
        "pgvector",
        "pinecone",
        "qdrant",
        "search backend",
        "search infrastructure",
        "weaviate",
    },
    "ranking": {
        "learning to rank",
        "ranking systems",
        "recommendation systems",
    },
    "fine_tuning": {
        "fine-tuning llms",
        "lora",
        "model adaptation",
        "peft",
        "qlora",
    },
    "ml_systems": {
        "bentoml",
        "feature engineering",
        "kubernetes",
        "machine learning",
        "mlflow",
        "mlops",
        "pytorch",
        "tensorflow",
        "workflow orchestration",
    },
}

# Each evidence family is independently capped.  Repeating "ranking" ten times
# cannot compensate for having no retrieval or evaluation experience.
EVIDENCE_PATTERNS: dict[str, tuple[tuple[str, str], ...]] = {
    "retrieval": (
        ("hybrid", "hybrid sparse/dense retrieval"),
        ("dense retrieval", "dense retrieval"),
        ("semantic search", "semantic search"),
        ("embedding-based search", "embedding-based search"),
        ("embedding-based retrieval", "embedding-based retrieval"),
        ("vector search", "vector search"),
        ("nearest-neighbor retrieval", "nearest-neighbor retrieval"),
        ("bm25", "BM25 retrieval"),
        ("faiss", "FAISS retrieval"),
        ("pinecone", "Pinecone retrieval"),
        ("query expansion", "query expansion"),
        ("index refresh", "index refresh operations"),
        ("embedding drift", "embedding drift monitoring"),
    ),
    "ranking": (
        ("learning-to-rank", "learning-to-rank"),
        ("learning to rank", "learning-to-rank"),
        ("ranking model", "ranking models"),
        ("ranking layer", "ranking ownership"),
        ("ranking pipeline", "ranking pipeline ownership"),
        ("recommendation system", "recommendation systems"),
        ("recommendation-style", "recommendation features"),
        ("recommendations-heavy", "recommendation systems"),
        ("personalization", "personalization systems"),
        ("re-ranking", "re-ranking"),
        ("rerank", "re-ranking"),
        ("relevance", "search relevance"),
        ("matching layer", "matching systems"),
    ),
    "evaluation": (
        ("ndcg", "NDCG evaluation"),
        ("mrr", "MRR evaluation"),
        ("recall@", "recall-at-K evaluation"),
        ("a/b test", "online A/B testing"),
        ("a/b testing", "online A/B testing"),
        ("offline-online", "offline/online metric correlation"),
        ("offline metrics", "offline evaluation"),
        ("offline evaluation", "offline evaluation"),
        ("eval framework", "evaluation frameworks"),
        ("evaluation framework", "evaluation frameworks"),
        ("relevance labeling", "relevance labeling"),
        ("human relevance", "human relevance judgments"),
        ("human judgments", "human relevance judgments"),
        ("recruiter-feedback", "recruiter feedback loops"),
    ),
    "production": (
        ("production", "production deployment"),
        ("shipped", "shipping production ML"),
        ("serving", "online serving"),
        ("deployed", "production deployment"),
        ("latency", "latency optimization"),
        ("p95", "latency optimization"),
        ("million", "large-scale systems"),
        ("billion", "large-scale systems"),
        ("monitoring", "production monitoring"),
        ("drift", "drift monitoring"),
        ("rollback", "safe rollout operations"),
        ("live engagement", "live product impact"),
    ),
    "ownership": (
        ("owned", "end-to-end ownership"),
        ("led", "technical leadership"),
        ("designed", "system design"),
        ("from scratch", "greenfield delivery"),
        ("worked closely with pm", "product collaboration"),
        ("product and growth", "product collaboration"),
        ("recruiter", "recruiting-product exposure"),
        ("mentored", "engineering mentorship"),
    ),
}

EVIDENCE_WEIGHTS = {
    "retrieval": 0.25,
    "ranking": 0.24,
    "evaluation": 0.22,
    "production": 0.18,
    "ownership": 0.11,
}


@dataclass
class RankedCandidate:
    candidate_id: str
    score: float
    title: str
    company: str
    location: str
    country: str
    years_experience: float
    role_score: float
    career_score: float
    skill_score: float
    experience_score: float
    company_score: float
    behavior_score: float
    logistics_score: float
    matched_skills: list[str] = field(default_factory=list)
    career_evidence: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    integrity_failures: list[str] = field(default_factory=list)
    last_active_date: str = ""
    response_rate: float = 0.0
    notice_period_days: int = 0
    open_to_work: bool = False
    willing_to_relocate: bool = False

def _normalise(value: Any) -> str:
    text = str(value or "").lower().replace("\u2014", "-").replace("\u2013", "-")
    return " ".join(text.split())


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def iter_candidates(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield candidates from JSONL, JSONL.GZ, JSON, or JSON.GZ input."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Candidate file does not exist: {source}")

    logical_suffix = source.with_suffix("").suffix.lower() if source.suffix.lower() == ".gz" else source.suffix.lower()
    with _open_text(source) as handle:
        if logical_suffix == ".jsonl":
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_number} of {source}: {exc}") from exc
                if not isinstance(candidate, dict):
                    raise ValueError(f"Line {line_number} of {source} is not a candidate object")
                yield candidate
            return

        if logical_suffix == ".json":
            try:
                candidates = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {source}: {exc}") from exc
            if not isinstance(candidates, list):
                raise ValueError(f"Expected a JSON array in {source}")
            for index, candidate in enumerate(candidates, start=1):
                if not isinstance(candidate, dict):
                    raise ValueError(f"Candidate {index} in {source} is not an object")
                yield candidate
            return

    raise ValueError(f"Unsupported candidate format for {source}; use .jsonl, .jsonl.gz, .json, or .json.gz")


def infer_reference_date(path: str | Path) -> tuple[date, int]:
    """Infer the dataset snapshot date from its latest activity timestamp."""
    latest: date | None = None
    count = 0
    for candidate in iter_candidates(path):
        count += 1
        active = _parse_date(candidate.get("redrob_signals", {}).get("last_active_date"))
        if active and (latest is None or active > latest):
            latest = active
    if count == 0:
        raise ValueError("Candidate input is empty")
    # Activity dates are generated up to the end of the prior month.  A short
    # offset avoids treating the latest profile as being active in the future.
    return (latest + timedelta(days=7) if latest else date.today()), count


def _role_fit(title: str) -> float:
    t = _normalise(title)
    exact = {
        "lead ai engineer": 1.00,
        "senior ai engineer": 1.00,
        "senior applied scientist": 0.97,
        "senior machine learning engineer": 1.00,
        "senior ml engineer - search & ranking": 1.00,
        "senior nlp engineer": 0.98,
        "staff machine learning engineer": 0.98,
        "recommendation systems engineer": 0.94,
        "search engineer": 0.94,
        "applied ml engineer": 0.92,
        "machine learning engineer": 0.90,
        "ai engineer": 0.88,
        "nlp engineer": 0.86,
        "senior data scientist": 0.74,
        "senior software engineer (ml)": 0.72,
        "ml engineer": 0.68,
        "data scientist": 0.58,
        "ai specialist": 0.54,
        "ai research engineer": 0.48,
        "computer vision engineer": 0.30,
        "junior ml engineer": 0.28,
        "ml platform engineer": 0.66,
    }
    if t in exact:
        return exact[t]
    if any(term in t for term in ("search", "ranking", "recommendation")) and "engineer" in t:
        return 0.88
    if "machine learning" in t or re.search(r"\bml\b", t):
        return 0.66
    if ("ai" in t or "nlp" in t) and any(term in t for term in ("engineer", "scientist")):
        return 0.62
    if "data engineer" in t or "software engineer" in t or "backend engineer" in t:
        return 0.24
    if "data analyst" in t or "analytics engineer" in t:
        return 0.14
    return 0.03


def _career_evidence(career_history: list[dict[str, Any]], summary: str) -> tuple[float, list[str], set[str]]:
    descriptions = " ".join(_normalise(role.get("description")) for role in career_history)
    # Summary adds context but cannot create a category by itself.  This stops a
    # polished headline from substituting for evidence in actual roles.
    context = f"{descriptions} {_normalise(summary)}"
    labels: list[str] = []
    hit_groups: set[str] = set()
    score = 0.0
    for group, patterns in EVIDENCE_PATTERNS.items():
        group_labels: list[str] = []
        for needle, label in patterns:
            if needle in descriptions:
                group_labels.append(label)
        if group_labels:
            hit_groups.add(group)
            score += EVIDENCE_WEIGHTS[group]
            # Keep one representative fact per JD dimension so explanations
            # cover breadth instead of listing three near-synonymous tools.
            labels.append(group_labels[0])

    # Partial credit for a profile summary that is corroborated by at least two
    # career-evidence families, never for summary keywords alone.
    if len(hit_groups) >= 2 and any(term in context for term in ("retrieval", "ranking", "recommendation", "search")):
        score = min(1.0, score + 0.04)
    return min(score, 1.0), labels, hit_groups


def _skill_quality(skill: dict[str, Any], assessment_scores: dict[str, Any]) -> float:
    proficiency = PROFICIENCY.get(_normalise(skill.get("proficiency")), 0.0)
    months = max(0, _as_int(skill.get("duration_months")))
    endorsements = max(0, _as_int(skill.get("endorsements")))
    duration_factor = min(1.0, months / 48.0)
    endorsement_factor = min(1.0, math.log1p(endorsements) / math.log(51))
    quality = proficiency * (0.68 + 0.22 * duration_factor + 0.10 * endorsement_factor)

    assessment = None
    skill_name = _normalise(skill.get("name"))
    for name, value in assessment_scores.items():
        if _normalise(name) == skill_name:
            assessment = _as_float(value) / 100.0
            break
    if assessment is not None:
        quality = 0.82 * quality + 0.18 * max(0.0, min(1.0, assessment))
    return max(0.0, min(1.0, quality))


def _skills_score(skills: list[dict[str, Any]], assessments: dict[str, Any]) -> tuple[float, list[str], dict[str, float]]:
    group_best = {group: 0.0 for group in SKILL_GROUPS}
    group_label: dict[str, str] = {}
    for skill in skills:
        name = _normalise(skill.get("name"))
        quality = _skill_quality(skill, assessments)
        for group, names in SKILL_GROUPS.items():
            if name in names and quality > group_best[group]:
                group_best[group] = quality
                group_label[group] = str(skill.get("name", "")).strip()

    weights = {
        "python": 0.18,
        "retrieval": 0.23,
        "vector_infra": 0.20,
        "ranking": 0.18,
        "fine_tuning": 0.07,
        "ml_systems": 0.14,
    }
    score = sum(group_best[group] * weight for group, weight in weights.items())
    priority = ("python", "retrieval", "vector_infra", "ranking", "ml_systems", "fine_tuning")
    labels = [group_label[group] for group in priority if group in group_label]
    return min(score, 1.0), labels, group_best


def _experience_fit(years: float) -> float:
    if 6.0 <= years <= 8.0:
        return 1.0
    if 5.0 <= years <= 9.0:
        return 0.90
    if 4.0 <= years <= 10.0:
        return 0.68
    if 3.0 <= years <= 12.0:
        return 0.36
    return 0.10


def _company_fit(profile: dict[str, Any], career_history: list[dict[str, Any]]) -> tuple[float, bool]:
    companies = [_normalise(role.get("company")) for role in career_history if role.get("company")]
    industries = [_normalise(role.get("industry")) for role in career_history]
    industries.append(_normalise(profile.get("current_industry")))
    consulting_only = bool(companies) and all(company in CONSULTING_COMPANIES for company in companies)
    product_roles = sum(company in PRODUCT_COMPANIES for company in companies)
    product_roles += sum(any(token in industry for token in PRODUCT_INDUSTRIES) for industry in industries)
    consulting_roles = sum(company in CONSULTING_COMPANIES for company in companies)
    if consulting_only:
        return 0.0, True
    if product_roles >= 2:
        return 1.0, False
    if product_roles == 1:
        return 0.78, False
    if companies and consulting_roles < len(companies):
        return 0.48, False
    return 0.25, False


def _behavior_fit(signals: dict[str, Any], reference_date: date) -> tuple[float, int]:
    response = max(0.0, min(1.0, _as_float(signals.get("recruiter_response_rate"))))
    active = _parse_date(signals.get("last_active_date"))
    inactive_days = max(0, (reference_date - active).days) if active else 3650
    if inactive_days <= 30:
        recency = 1.0
    elif inactive_days <= 90:
        recency = 0.78
    elif inactive_days <= 180:
        recency = 0.38
    else:
        recency = 0.0

    notice = max(0, _as_int(signals.get("notice_period_days"), 180))
    if notice <= 30:
        notice_score = 1.0
    elif notice <= 60:
        notice_score = 0.72
    elif notice <= 90:
        notice_score = 0.42
    else:
        notice_score = 0.10

    open_score = 1.0 if signals.get("open_to_work_flag") is True else 0.22
    interview = max(0.0, min(1.0, _as_float(signals.get("interview_completion_rate"))))
    applications = min(1.0, max(0, _as_int(signals.get("applications_submitted_30d"))) / 10.0)
    saves = min(1.0, max(0, _as_int(signals.get("saved_by_recruiters_30d"))) / 20.0)
    github_raw = _as_float(signals.get("github_activity_score"), -1.0)
    github = 0.25 if github_raw < 0 else min(1.0, github_raw / 80.0)
    verified = (int(signals.get("verified_email") is True) + int(signals.get("verified_phone") is True)) / 2.0

    score = (
        0.30 * response
        + 0.20 * recency
        + 0.15 * open_score
        + 0.15 * notice_score
        + 0.08 * interview
        + 0.04 * applications
        + 0.03 * saves
        + 0.03 * github
        + 0.02 * verified
    )
    return max(0.0, min(1.0, score)), inactive_days


def _logistics_fit(profile: dict[str, Any], signals: dict[str, Any]) -> float:
    country = _normalise(profile.get("country"))
    location = _normalise(profile.get("location"))
    relocate = signals.get("willing_to_relocate") is True
    in_india = country in INDIA_COUNTRY_NAMES
    preferred = any(city in location for city in PREFERRED_CITIES)
    if in_india and preferred:
        return 1.0
    if in_india and relocate:
        return 0.86
    if in_india:
        return 0.58
    if relocate:
        return 0.32
    return 0.05


def integrity_failures(candidate: dict[str, Any]) -> list[str]:
    profile = candidate.get("profile", {})
    career_history = candidate.get("career_history", []) or []
    skills = candidate.get("skills", []) or []
    failures: list[str] = []

    if any(
        _normalise(skill.get("proficiency")) == "expert" and _as_int(skill.get("duration_months"), -1) == 0
        for skill in skills
    ):
        failures.append("expert skills report zero usage duration")

    years = _as_float(profile.get("years_of_experience"))
    career_years = sum(max(0, _as_int(role.get("duration_months"))) for role in career_history) / 12.0
    if career_history and abs(years - career_years) > 2.0:
        failures.append("claimed experience conflicts with the career timeline")

    summary_match = YEARS_RE.search(str(profile.get("summary", "")))
    if summary_match and abs(years - _as_float(summary_match.group(1))) > 2.0:
        failures.append("profile and summary state contradictory experience")

    for role in career_history:
        company = _normalise(role.get("company"))
        start = _parse_date(role.get("start_date"))
        founded = COMPANY_FOUNDING_YEAR.get(company)
        if start and founded and start.year < founded:
            failures.append(f"employment at {role.get('company')} predates the company")
            break

    return failures


def _is_non_technical_title(title: str) -> bool:
    t = _normalise(title)
    return any(term in t for term in NON_TECH_TITLE_TERMS) or not any(term in t for term in TECHNICAL_TITLE_TERMS)


def _title_chasing(career_history: list[dict[str, Any]]) -> bool:
    durations = [max(0, _as_int(role.get("duration_months"))) for role in career_history]
    return len(durations) >= 3 and median(durations) < 18


def score_candidate(candidate: dict[str, Any], reference_date: date) -> RankedCandidate:
    candidate_id = str(candidate.get("candidate_id", "")).strip()
    if not CANDIDATE_ID_RE.fullmatch(candidate_id):
        raise ValueError(f"Invalid or missing candidate_id: {candidate_id!r}")

    profile = candidate.get("profile", {}) or {}
    career_history = candidate.get("career_history", []) or []
    skills = candidate.get("skills", []) or []
    signals = candidate.get("redrob_signals", {}) or {}
    title = str(profile.get("current_title", "Unknown")).strip() or "Unknown"
    company = str(profile.get("current_company", "Unknown")).strip() or "Unknown"
    years = max(0.0, _as_float(profile.get("years_of_experience")))

    role_score = _role_fit(title)
    career_score, evidence, evidence_groups = _career_evidence(career_history, str(profile.get("summary", "")))
    skill_score, matched_skills, skill_groups = _skills_score(skills, signals.get("skill_assessment_scores", {}) or {})
    experience_score = _experience_fit(years)
    company_score, consulting_only = _company_fit(profile, career_history)
    behavior_score, inactive_days = _behavior_fit(signals, reference_date)
    logistics_score = _logistics_fit(profile, signals)
    integrity = integrity_failures(candidate)

    score = 100.0 * (
        0.23 * role_score
        + 0.30 * career_score
        + 0.14 * skill_score
        + 0.10 * experience_score
        + 0.08 * company_score
        + 0.10 * behavior_score
        + 0.05 * logistics_score
    )

    concerns: list[str] = []
    ai_skill_groups = sum(skill_groups[group] > 0.0 for group in ("retrieval", "vector_infra", "ranking", "fine_tuning"))
    if _is_non_technical_title(title) and ai_skill_groups >= 2:
        score -= 45.0
        concerns.append("AI keywords are not supported by a technical role history")
    if consulting_only:
        score -= 10.0
        concerns.append("career history is limited to consulting/services firms")
    if _title_chasing(career_history):
        score -= 3.5
        concerns.append("several short role tenures")
    if role_score <= 0.48 and ("retrieval" not in evidence_groups and "ranking" not in evidence_groups):
        score -= 8.0
        concerns.append("limited production search or ranking evidence")
    if "computer vision" in _normalise(title) and not ({"retrieval", "ranking"} & evidence_groups):
        score -= 8.0
        concerns.append("experience is primarily computer vision rather than NLP/IR")
    if "research" in _normalise(title) and "production" not in evidence_groups:
        score -= 8.0
        concerns.append("research profile lacks production deployment evidence")
    if inactive_days > 180 and _as_float(signals.get("recruiter_response_rate")) < 0.10:
        score -= 9.0
        concerns.append("inactive for over six months with a very low response rate")
    if signals.get("open_to_work_flag") is not True:
        concerns.append("not currently marked open to work")
        if inactive_days > 120 and _as_float(signals.get("recruiter_response_rate")) < 0.20:
            score -= 6.0
    notice = max(0, _as_int(signals.get("notice_period_days"), 180))
    if notice > 30:
        concerns.append(f"{notice}-day notice exceeds the JD preference")
    country = _normalise(profile.get("country"))
    if country not in INDIA_COUNTRY_NAMES and signals.get("willing_to_relocate") is not True:
        score -= 4.0
        concerns.append("outside India and not willing to relocate")
    elif logistics_score < 0.8:
        concerns.append("outside the preferred hubs")
    if years < 5.0 or years > 9.0:
        concerns.append(f"{years:.1f} years is outside the preferred 5-9 year range")

    if integrity:
        # Honeypots are relevance tier 0 by rule.  Preserve a small differentiated
        # score for deterministic ordering while keeping them far outside top 100.
        score = min(5.0, max(0.0, score * 0.04))
        concerns = integrity + concerns

    return RankedCandidate(
        candidate_id=candidate_id,
        score=max(0.0, score),
        title=title,
        company=company,
        location=str(profile.get("location", "Unknown")).strip() or "Unknown",
        country=str(profile.get("country", "Unknown")).strip() or "Unknown",
        years_experience=years,
        role_score=role_score,
        career_score=career_score,
        skill_score=skill_score,
        experience_score=experience_score,
        company_score=company_score,
        behavior_score=behavior_score,
        logistics_score=logistics_score,
        matched_skills=matched_skills,
        career_evidence=evidence,
        concerns=concerns,
        integrity_failures=integrity,
        last_active_date=str(signals.get("last_active_date", "")),
        response_rate=max(0.0, min(1.0, _as_float(signals.get("recruiter_response_rate")))),
        notice_period_days=notice,
        open_to_work=signals.get("open_to_work_flag") is True,
        willing_to_relocate=signals.get("willing_to_relocate") is True,
    )


def rank_candidates(path: str | Path, reference_date: date | None = None) -> tuple[list[RankedCandidate], date]:
    if reference_date is None:
        reference_date, _ = infer_reference_date(path)

    seen: set[str] = set()
    ranked: list[RankedCandidate] = []
    for candidate in iter_candidates(path):
        result = score_candidate(candidate, reference_date)
        if result.candidate_id in seen:
            raise ValueError(f"Duplicate candidate_id in input: {result.candidate_id}")
        seen.add(result.candidate_id)
        ranked.append(result)
    if not ranked:
        raise ValueError("Candidate input is empty")
    ranked.sort(key=lambda item: (-round(item.score, 8), item.candidate_id))
    return ranked, reference_date


def generate_reasoning(candidate: RankedCandidate) -> str:
    evidence = candidate.career_evidence[:3]
    skills = candidate.matched_skills[:3]
    first = f"{candidate.years_experience:.1f} years of experience; currently {candidate.title} at {candidate.company}"
    if evidence:
        first += ", with career evidence of " + ", ".join(evidence)
    elif skills:
        first += ", with relevant listed skills in " + ", ".join(skills)
    first += "."

    behavior_bits = []
    if candidate.last_active_date:
        behavior_bits.append(f"active {candidate.last_active_date}")
    behavior_bits.append(f"{candidate.response_rate:.0%} recruiter response rate")
    behavior_bits.append(f"{candidate.notice_period_days}-day notice")
    second = "Platform signals show " + ", ".join(behavior_bits)
    if candidate.concerns:
        second += f"; main concern: {candidate.concerns[0]}"
    else:
        second += "; no material JD-specific concern is evident"
    second += "."
    return first + " " + second


def write_submission(ranked: list[RankedCandidate], output_path: str | Path, limit: int = 100) -> int:
    if limit < 1:
        raise ValueError("Output limit must be at least 1")
    selected = ranked[: min(limit, len(ranked))]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for rank, candidate in enumerate(selected, start=1):
            writer.writerow(
                {
                    "candidate_id": candidate.candidate_id,
                    "rank": rank,
                    "score": f"{round(candidate.score, 8):.8f}",
                    "reasoning": generate_reasoning(candidate),
                }
            )
    return len(selected)
