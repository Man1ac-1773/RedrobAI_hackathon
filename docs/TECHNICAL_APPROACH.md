# Technical Approach

## Executive Summary

This submission uses a deterministic evidence-ranking pipeline for the Senior AI
Engineer role. It does not use a hosted model, a local language model, dense
embeddings, candidate-specific rules, or network access during ranking. The direct
path reads the candidate file supplied on the command line and ranks 100,000
profiles in about 17 seconds on the declared CPU.

The central modeling decision is to treat career history as stronger evidence than
the skills list. The job description explicitly warns that keyword coverage is a
trap: a candidate who operated ranking and retrieval systems is more relevant than
a candidate who merely lists RAG, Pinecone, or LangChain. The score therefore puts
30% of its base weight on production career evidence and caps every skill family.

## End-to-End Data Flow

```text
candidate JSON/JSONL
        |
        v
format and ID validation ----> fail clearly on malformed/duplicate IDs
        |
        v
structured feature extraction
        |
        +--> integrity checks (impossible dates, contradictory experience)
        +--> career evidence (retrieval, ranking, evaluation, production, ownership)
        +--> role and product-company fit
        +--> credible skill depth (proficiency + duration + endorsements + assessment)
        +--> experience, behavioral availability, and logistics
        |
        v
weighted score + explicit penalties
        |
        v
deterministic sort: score descending, candidate_id ascending
        |
        v
top 100 + grounded two-sentence reasoning
        |
        v
candidate_id,rank,score,reasoning CSV
```

The implementation is split between `rank.py`, the stable command-line contract,
and `ranking_core.py`, which owns parsing, feature extraction, scoring, integrity
checks, deterministic sorting, and explanation generation.

## Scoring Function

Before penalties, the score is:

```text
100 * (
    0.30 * career_evidence
  + 0.23 * role_fit
  + 0.14 * skill_depth
  + 0.10 * experience_fit
  + 0.10 * behavioral_availability
  + 0.08 * product_company_fit
  + 0.05 * location_logistics
)
```

Each component is bounded to `[0, 1]`. Keeping the components independent and
capped prevents one repeated signal from dominating the entire ranking.

### Career Evidence: 30%

Career descriptions are evaluated across five separately capped families:

| Family | Share of career component | Examples of accepted evidence |
| --- | ---: | --- |
| Retrieval | 25% | hybrid/dense retrieval, semantic search, BM25, vector search, index refresh, embedding drift |
| Ranking | 24% | learning-to-rank, recommendation systems, re-ranking, personalization, matching systems |
| Evaluation | 22% | NDCG, MRR, recall@K, offline/online correlation, A/B testing, relevance judgments |
| Production | 18% | deployment, serving, scale, latency, monitoring, drift, rollback paths |
| Ownership | 11% | owned, led, designed, greenfield delivery, PM/recruiter collaboration, mentorship |

The profile summary cannot create an evidence family by itself. It receives only a
small corroboration bonus after at least two families are present in actual career
descriptions. This is the main anti-keyword-stuffing control.

### Role Fit: 23%

Role fit is strongest for hands-on senior search, ranking, recommendation, NLP, and
ML engineering roles. It is deliberately not a binary title filter: a less obvious
title can still rank well through strong career evidence. Research-only, CV-only,
generic software, and non-technical roles receive lower priors and must provide
substantial corroborating evidence.

### Skill Depth: 14%

Skills are grouped into Python, retrieval, vector infrastructure, ranking,
fine-tuning, and ML systems. Only the strongest credible skill in each family is
used. Credibility combines:

- declared proficiency;
- months of use;
- endorsements;
- the matching Redrob assessment score, when present.

This means listing five vector databases cannot earn five times the vector score.
An expert claim with zero months of use is an integrity failure rather than a
positive signal.

### Experience and Company Context: 18%

Experience is strongest at 6-8 years, remains high across the stated 5-9 year
preference, and gives partial credit outside the range because the JD explicitly
says it is not a hard requirement.

Company context rewards product experience and applies the JD's consulting-only
exclusion. A candidate currently at a services firm is not excluded when earlier
product-company experience is present.

### Behavioral Availability and Logistics: 15%

Behavior is a modifier after technical relevance. It combines last activity,
recruiter response rate, open-to-work status, notice period, interview completion,
applications, recruiter saves, GitHub activity, and verification. A highly active
but irrelevant profile cannot overcome a low technical score.

Logistics follows the JD: Pune/Noida and the named Indian hubs score highest,
India-based candidates willing to relocate remain strong, and candidates outside
India without relocation intent are penalized.

## Integrity and Trap Handling

Integrity checks are structural and never use candidate IDs. The following
conditions cap a profile below score 5:

1. An expert skill reports zero months of use.
2. Claimed years of experience differ materially from the career timeline.
3. The summary and profile state contradictory years of experience.
4. Employment starts before a known company's founding year for the companies
   implicated by the published honeypot warning.

Additional penalties cover non-technical AI keyword stuffing, consulting-only
careers, pure research without production deployment, CV specialization without
NLP/IR evidence, repeated short tenures, severe inactivity, and unavailable
location/relocation combinations.

The generated full-pool top 100 contains zero profiles that fail an integrity
check. The integrity cap is intentionally stronger than an ordinary relevance
penalty because the challenge specification assigns honeypots relevance tier 0.

## Explanation Generation

Reasoning is generated after ranking from the same structured evidence used by the
score. Each explanation contains two sentences:

1. Grounded static evidence: years of experience, current title and company, then
   up to three distinct JD dimensions found in career history.
2. Grounded availability evidence: activity date, recruiter response rate, notice
   period, and the highest-priority concern.

The generator never invents a skill or employer. Evidence labels are emitted only
after their corresponding phrase is found in career history. The final top 100 has
100 unique reasoning strings. This directly addresses the Stage 4 checks for
specificity, JD connection, concerns, hallucination avoidance, and variation.

## Reproducibility and Generalization

The final scoring set is the released candidate pool with hidden relevance labels;
the specification does not define a second hidden candidate pool. Stage 3 can still
rerun the command, and the hosted demo must accept a small supplied sample.

The implementation therefore does not assume the released file name or candidate
IDs. It supports JSON, JSONL, and gzip variants, infers a reference date from the
input's activity timestamps, validates duplicate IDs, and ranks any schema-
compatible input. Small samples emit all available candidates; pools of 100 or more
emit exactly 100.

An optional precomputed artifact is available for repeated runs, but direct ranking
does not depend on it. Artifacts contain the source SHA-256, scoring version,
reference date, and record count. A mismatched or stale artifact fails loudly.

## Complexity and Constraints

- Time complexity: `O(N log N)` because all candidates are scored once and sorted.
- Working memory: `O(N)` for compact scored records; measured below 190 MiB for
  100,000 candidates.
- Network: no network imports or calls in the ranking path.
- Compute: CPU only; no model runtime or GPU package.
- Intermediate disk: only the requested CSV in direct mode.
- Dependencies: Python 3.10+ standard library only.
- Determinism: displayed score descending, then candidate ID ascending for ties.

Measured full-pool execution was 17.4 seconds, leaving substantial margin under the
five-minute and 16 GB limits. A second independent run produced a byte-identical
CSV with SHA-256 `dbb89a05afdabeda59d8bbeaa620c276e302c331f4772f858f6b972eb2a20966`.

## Deliberate Tradeoffs

The scorer favors auditability and robust structured evidence over opaque semantic
similarity. A dense model could recover paraphrases that the phrase families miss,
but it also amplifies the exact keyword and honeypot failures highlighted by the
challenge. The released profiles contain explicit production narratives, so the
evidence-family approach provides a strong quality/latency/reproducibility balance.

Company and role priors are intentionally modest relative to career evidence. They
encode JD-specific preferences, not universal candidate quality. Every decisive
penalty is visible in code and reflected in the candidate's explanation where it is
relevant.
