# Redrob Hackathon: Intelligent Candidate Discovery & Ranking

This repository contains my team's submission for the Intelligent Candidate Discovery & Ranking Challenge. 
The goal is to identify the top 100 candidates for a "Senior AI Engineer" role from a dataset of 100,000 resumes, strictly adhering to compute constraints (CPU-only, < 5 minutes runtime) and without relying on paid LLM APIs.

## My Approach & Architecture

To meet the strict 5-minute CPU-only compute limit and scalably handle the 100k candidate pool while avoiding paid API keys, I designed a **Hybrid Offline-Online Architecture**.

### 1. Offline Pre-processing (`offline_preprocess.py`)
This step is run once to prepare the dataset.
- **Data Cleaning & Filtering:** I automatically filter out explicit "honeypots" (e.g., claiming expert proficiency with 0 months duration) and "keyword stuffers" (e.g., non-engineering roles like Marketing Managers claiming AI expertise).
- **Embeddings Calculation:** I compute dense semantic embeddings for each candidate using the lightweight, open-source `all-MiniLM-L6-v2` model.
- **Behavioral Multipliers:** I calculate behavioral signals based on candidate tenure and experience consistency.
- **Output:** The pre-processed dataset is saved as a serialized file (`precomputed_data.pkl`), containing 96k clean candidates. 

### 2. Online Ranking (`rank.py`)
This is the script executed for the final evaluation.
- **Rapid Scoring:** It loads the pre-computed embeddings and embeds the target Job Description on the fly.
- **Similarity & Ranking:** It computes cosine similarity between the candidate embeddings and the JD, applies the behavioral signal multiplier, and returns the top 100 candidates.
- **Performance:** This online step easily runs well under the 5-minute CPU limit.

## Repository Structure
- `rank.py`: The main script to generate the top 100 candidates (`submission.csv`). Pure numpy, < 5 min runtime.
- `offline_preprocess.py`: The script used to generate the precomputed embeddings and multipliers.
- `sample_precomputed_data.pkl`: A lightweight subset (50 candidates) for quick testing or Colab demos.
- `submission_metadata.yaml`: Configuration metadata for the submission.

## Setup & Reproduction

### Local Environment Setup
We use `uv` for fast package management, but standard `pip` works too.

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Or using uv: `uv sync`)*

### 1. Pre-computation Step (Offline)
Because our full `precomputed_data.pkl` is ~367 MB (exceeding GitHub's 100 MB file limit), we provide the script that generates it, strictly adhering to Section 10.3 of the spec ("include pre-computed artifacts... or a script that produces them").

Before ranking, run the pre-processor to generate the embeddings:
```bash
python offline_preprocess.py
```
*(This may take 15-30 minutes and downloads huggingface weights. This step happens entirely offline).*

### 2. Running the Ranking Script (Evaluation)
To reproduce the submission CSV (`submission.csv`) from the candidates file, run the following single command:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```
> **Note:** As permitted by the spec, `rank.py` will read from the generated `precomputed_data.pkl`. It runs entirely locally on CPU, uses no network (no huggingface API calls), and finishes in under 1 minute.

### Running the Demo on Google Colab
If evaluators want to try out the sandbox : 
Visit this Colab Notebook : 
And follow the instructions! (run the cells).

- **Declaration**: This project was created with the help of Google Gemini.
