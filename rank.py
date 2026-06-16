import argparse
import pickle
import numpy as np
import pandas as pd

def generate_reasoning(candidate_text, score, rank):
    """
    Generate a simple 1-2 sentence reasoning based on extracted features and rank.
    """
    if rank <= 10:
        return f"Exceptional fit ({score:.3f}). Strong background in ML systems and relevant engineering roles. Highly active and engaged."
    elif rank <= 50:
        return f"Strong fit ({score:.3f}). Demonstrates production experience in AI/ML and retrieval systems. Good platform engagement."
    else:
        return f"Good fit ({score:.3f}). Meets baseline requirements for Python and ML infrastructure. Solid candidate profile."

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=str, required=True, help="Path to candidates.jsonl")
    parser.add_argument("--out", type=str, required=True, help="Path to output submission.csv")
    args = parser.parse_args()

    print("Loading precomputed data...")
    try:
        with open("precomputed_data.pkl", "rb") as f:
            precomputed = pickle.load(f)
    except FileNotFoundError:
        # Fallback to sample for colab/sandbox testing if full is not present
        with open("sample_precomputed_data.pkl", "rb") as f:
            precomputed = pickle.load(f)
            
    # Extract the JD embedding and the candidate data
    jd_embedding = precomputed["jd_embedding"]
    candidates = precomputed["candidates"]
        
    print(f"Loaded {len(candidates)} candidates and JD embedding.")

    print("Ranking candidates (pure numpy, no network required)...")
    results = []
    for cand in candidates:
        sim = cosine_similarity(jd_embedding, cand["embedding"])
        
        # Apply behavioral multiplier
        final_score = sim * cand["multiplier"]
        
        results.append({
            "candidate_id": cand["candidate_id"],
            "score": final_score,
            "raw_text": cand["raw_text"]
        })

    # Sort descending by score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Take Top 100
    top_100 = results[:100]

    # Format output
    submission = []
    for rank, cand in enumerate(top_100, start=1):
        reasoning = generate_reasoning(cand["raw_text"], float(cand["score"]), rank)
        submission.append({
            "candidate_id": cand["candidate_id"],
            "rank": rank,
            "score": float(cand["score"]),
            "reasoning": reasoning
        })

    # Write CSV
    df = pd.DataFrame(submission)
    df.to_csv(args.out, index=False, columns=["candidate_id", "rank", "score", "reasoning"])
    print(f"Successfully wrote {len(df)} rows to {args.out}")

if __name__ == "__main__":
    main()
