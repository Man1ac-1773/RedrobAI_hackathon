# Redrob Hackathon: Antigravity Pipeline

This repository contains our team's submission for the Intelligent Candidate Discovery & Ranking Challenge.

## Pipeline Architecture
To meet the strict 5-minute CPU-only compute limits and handle the 100k candidate pool scalably, we split our architecture:
1. **Offline Pre-processing (`offline_preprocess.py`)**: Extracted text features, dropped explicit honeypots and non-engineering keyword stuffers, computed dense embeddings using `all-MiniLM-L6-v2`, and calculated behavioral scalar multipliers. The result is stored in `precomputed_data.pkl`.
2. **Online Ranking (`rank.py`)**: Loads the pre-computed embeddings, embeds the Job Description, and uses rapid Cosine Similarity scoring multiplied by the behavioral signal to rank the top 100 candidates.

## Reproduction
To reproduce the submission CSV from the candidates file, ensure the Python environment is set up (via `uv sync` or `pip install -r requirements.txt`).

**The single command to produce the submission:**
```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```
*(Note: Because we use a pre-computed data approach to bypass the 5-minute LLM scaling bottleneck, `rank.py` will read from `precomputed_data.pkl` which is included in this repository).*
