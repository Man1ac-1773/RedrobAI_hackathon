# Redrob Intelligent Candidate Ranking

This repository ranks the released candidate pool for Redrob's Senior AI Engineer
role. The ranking command is deterministic, CPU-only, makes no network calls, and
uses only the Python standard library.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Man1ac-1773/RedrobAI_hackathon/blob/master/demo.ipynb)

## Reproduce the submission

Python 3.10 or newer is required. There are no third-party runtime dependencies.

```bash
python3 rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

The command reads the file supplied through `--candidates`; it does not rely on a
bundled copy of the candidate pool or silently substitute sample data. Supported
inputs are `.jsonl`, `.jsonl.gz`, `.json`, and `.json.gz`.

Generated CSVs and the released candidate dataset are intentionally ignored by
Git: the evaluator supplies the candidate file, and the command above recreates
the output without a hidden or manually edited artifact.

For an official pool of at least 100 candidates, the command emits exactly 100
rows. A smaller sandbox sample emits every available candidate and warns that the
result is a demo rather than a validator-ready final submission.

Validate the result with the organizer's script:

```bash
python3 validate_submission.py ./submission.csv
```

Run the repository's broader automated compliance check:

```bash
python3 preflight.py --candidates ./candidates.jsonl
```

The preflight executes the real ranking command with a five-minute timeout, checks
the CSV contract, source-ID membership, deterministic ordering, explanation
grounding and uniqueness, integrity failures, required repository files, metadata
consistency, dependencies, and forbidden network/heavy imports.

## Ranking method

The scorer implements the gap between the words in the JD and the evidence the JD
actually asks for. Each candidate receives a weighted score from seven independent
dimensions:

| Dimension | Weight | Evidence used |
| --- | ---: | --- |
| Career evidence | 30% | Production retrieval, ranking, evaluation, deployment, and ownership described in career history |
| Role fit | 23% | Current role proximity to hands-on search, recommendation, NLP, and ML engineering |
| Verified skill depth | 14% | Proficiency, duration, endorsements, and Redrob assessment scores, capped by skill family |
| Experience | 10% | Preference for 5-9 years, strongest around 6-8, without making the range a hard filter |
| Redrob behavior | 10% | Recency, response rate, open-to-work status, notice period, interview completion, and activity |
| Product background | 8% | Product-company experience and the JD's consulting-only exclusion |
| Location/logistics | 5% | India, preferred hubs, and willingness to relocate |

Career evidence has the largest weight and self-declared skill families are capped.
This prevents a long list of AI keywords from outranking someone who has shipped a
search or recommendation system and measured it in production.

The scorer also applies explicit, reviewable penalties for:

- impossible company/employment timelines;
- expert skills with zero usage duration;
- contradictory claimed experience and career duration;
- non-technical profiles stuffed with advanced AI skills;
- consulting-only careers, pure research, or CV-only work without production IR;
- repeated short tenures, prolonged inactivity, and low availability.

Profiles that fail an integrity check are held below a score of 5, keeping likely
honeypots out of the top 100 without hardcoding candidate IDs.

## Reasoning quality

Every output row receives two candidate-specific sentences. The first cites the
candidate's title, employer, experience, and actual career evidence tied to the JD.
The second cites activity, recruiter response rate, notice period, and the most
important concern. Reasoning is generated only from fields present in that
candidate's record.

## Reproducibility and unseen inputs

The final evaluation is specified against the released candidate pool with hidden
relevance labels; the guidelines do not describe a separate hidden candidate test
set. Stage 3 may rerun the released pool, while the required hosted sandbox runs on
a supplied sample of at most 100 candidates.

The implementation nevertheless supports a different candidate file end-to-end:
it infers the dataset snapshot date from platform activity, validates IDs and
duplicates, scores the supplied records, and uses candidate ID ascending for exact
score ties. Nothing in the ranking path depends on released candidate IDs.

## Tests and benchmark

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile rank.py ranking_core.py preflight.py EDA/eda_script.py
```

Measured on the declared local CPU with the released 100,000-candidate JSONL:

- wall-clock ranking time: 17.4 seconds;
- peak resident memory: under 190 MiB;
- GPU: none;
- network during ranking: none;
- intermediate disk during direct ranking: only the output CSV.

The included [demo notebook](demo.ipynb) downloads only `rank.py`,
`ranking_core.py`, and the organizer-provided
[50-candidate sample](sample_candidates.json) from raw GitHub. It can instead
accept an uploaded candidate sample, validates the sample-sized output contract,
previews the reasoning, and downloads the CSV. No repository clone or package
installation is required.

For reviewer-facing implementation detail, see the
[technical approach](docs/TECHNICAL_APPROACH.md) and the
[requirement-by-requirement checklist](docs/SUBMISSION_CHECKLIST.md).

## Repository layout

- `rank.py`: official command-line entry point.
- `ranking_core.py`: parsing, scoring, integrity checks, ranking, and reasoning.
- `preflight.py`: executable repository, runtime, CSV, and reasoning audit.
- `demo.ipynb`, `sample_candidates.json`: self-contained hosted demonstration using the organizer's sample.
- `tests/test_ranking.py`: focused correctness and reproducibility tests.
- `submission_metadata.yaml`: environment and methodology declaration.
- `docs/`: detailed technical design and submission compliance map.
- `EDA/`: exploratory analysis of the released pool.

AI assistance declaration: Gemini and ChatGPT/Codex were used for code review,
debugging, and implementation support. The ranking logic is deterministic and can
be inspected and reproduced without an AI service.
