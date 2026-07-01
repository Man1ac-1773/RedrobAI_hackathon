# Submission Compliance Checklist

This document maps each published requirement to executable evidence in the
repository. Run the preflight command before uploading the CSV or changing portal
metadata.

```bash
python3 preflight.py --candidates ./candidates.jsonl
```

## CSV Contract

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Header is `candidate_id,rank,score,reasoning` | `ranking_core.OUTPUT_COLUMNS` | `preflight.py` and organizer validator |
| Exactly 100 rows for the released pool | `write_submission(..., limit=100)` | Preflight row-count check |
| Unique candidate IDs from the supplied pool | Input and output ID checks | Preflight source-membership check |
| Ranks are exactly 1-100 | Sequential enumeration after deterministic sort | Preflight rank check |
| Scores are non-increasing | Sort by displayed score descending | Preflight monotonicity check |
| Deterministic ties | Candidate ID ascending after rounded score | Unit test and preflight tie check |
| UTF-8 CSV with proper quoting | Standard-library `csv.DictWriter` | CSV parser round trip |

## Compute Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| At most 5 minutes | Pass | 17.4 seconds measured on 100,000 candidates |
| At most 16 GB RAM | Pass | Under 190 MiB peak RSS measured |
| CPU only | Pass | No GPU/model dependency; standard library only |
| Network off | Pass | No network import or call in `rank.py`/`ranking_core.py` |
| At most 5 GB intermediate disk | Pass | Direct mode writes only the output CSV |

## Repository Contract

| Required item | Location |
| --- | --- |
| Clear setup and exact reproduction command | `README.md` |
| Full ranking source | `rank.py`, `ranking_core.py` |
| Optional precomputation source | `offline_preprocess.py` |
| Dependency declaration and lock | `pyproject.toml`, `uv.lock` |
| Portal metadata mirror | `submission_metadata.yaml` |
| Hosted sandbox entry point | `demo.ipynb` and metadata Colab URL |
| Small preloaded sandbox input | `demo_candidates.jsonl` |
| Technical methodology | `docs/TECHNICAL_APPROACH.md` |
| Dataset audit | `EDA/EDA_report.md`, `EDA/eda_script.py` |
| Automated tests | `tests/` |
| Automated submission audit | `preflight.py` |

No precomputed artifact is required. The official command reads the candidate file
directly, so a missing pickle, model weight, or embedding index cannot break Stage
3 reproduction.

## Reasoning Review Contract

| Stage 4 check | How it is addressed |
| --- | --- |
| Specific facts | Every explanation includes experience, title, employer, and exact platform values |
| JD connection | Career evidence is selected from retrieval, ranking, evaluation, production, and ownership families |
| Honest concerns | The most important availability, experience, location, or career concern is stated |
| No hallucination | Explanations are generated only from parsed candidate fields and matched career phrases |
| Variation | Facts and evidence differ by candidate; preflight requires high uniqueness |
| Rank consistency | Explanations use the same scored evidence and penalties that determine rank |

## Final Operator Checks

These checks cannot be guaranteed by source code and must be confirmed at upload:

- The submitted CSV is the freshly generated file, not the sample or ODS file.
- The portal team name, contact details, repository URL, sandbox URL, and AI-tool
  declaration match `submission_metadata.yaml` exactly.
- The GitHub repository is public or organizer access has been granted.
- The Colab URL opens without requesting repository credentials.
- The portal filename follows the participant-ID naming instruction shown during
  upload.
- The organizer validator prints `Submission is valid.` for the final CSV.
- The upload is intentional because only three submissions are allowed and the
  latest valid submission becomes final.

## Verified Release Snapshot

- Full-pool rows read: 100,000
- Output rows: 100
- Top-100 integrity failures: 0
- Unique top-100 reasoning strings: 100
- India-based candidates: 97
- Deterministic CSV SHA-256:
  `dbb89a05afdabeda59d8bbeaa620c276e302c331f4772f858f6b972eb2a20966`
- Unit tests: 7 passing
- Organizer CSV validator: passing

Regenerate these measurements if scoring code or the candidate dataset changes.
