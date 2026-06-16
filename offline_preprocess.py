import json
import gzip
import pickle
import numpy as np
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

DATA_PATH = "resources/[PUB] India_runs_data_and_ai_challenge/candidates.jsonl" # For evaluators: Remember to edit this, this is the path on my local system
OUTPUT_PATH = "precomputed_data.pkl"

AI_KEYWORDS = {"NLP", "Fine-tuning LLMs", "Image Classification", "RAG", "Pinecone", "Milvus", "Vector Database", "PyTorch", "Transformers", "LLMs", "LangChain"}

def load_and_filter_candidates(filepath):
    print("Loading and filtering candidates...")
    valid_candidates = []
    
    with open(filepath, "rt") as f:
        for line in f:
            c = json.loads(line)
            profile = c.get("profile", {})
            title = profile.get("current_title", "Unknown")
            skills = c.get("skills", [])
            
            # --- Hard Filter 1: Honeypots ---
            is_honeypot = False
            for s in skills:
                if s.get("proficiency") == "expert" and s.get("duration_months", -1) == 0:
                    is_honeypot = True
                    break
            if is_honeypot:
                continue # Drop honeypot
                
            # --- Hard Filter 2: Non-tech keyword stuffers ---
            is_non_tech = ("Manager" in title and "Engineering" not in title) or "Accountant" in title or "Support" in title or "Sales" in title or "Writer" in title
            has_advanced_ai = any(s.get("name") in AI_KEYWORDS and s.get("proficiency") in ["advanced", "expert"] for s in skills)
            if is_non_tech and has_advanced_ai:
                continue # Drop keyword stuffers
                
            valid_candidates.append(c)
            
    print(f"Filtered down to {len(valid_candidates)} viable candidates.")
    return valid_candidates

def extract_text_features(candidate):
    """Combine profile info into a single dense text string for embedding."""
    profile = candidate.get("profile", {})
    summary = profile.get("summary", "")
    title = profile.get("current_title", "")
    
    # Extract top skills
    skills = candidate.get("skills", [])
    skills_str = ", ".join([s.get("name", "") for s in skills if s.get("proficiency") in ["advanced", "expert"]])
    
    # Extract recent experience highlights
    history = candidate.get("career_history", [])
    history_str = ""
    for role in history[:2]: # top 2 roles
        history_str += f"{role.get('title', '')} at {role.get('company', '')}: {role.get('description', '')}. "
        
    full_text = f"Title: {title}. Summary: {summary}. Top Skills: {skills_str}. Experience: {history_str}"
    return full_text

def calculate_behavioral_multiplier(candidate):
    """
    Calculate a scalar between 0.0 and 1.5 based on engagement.
    If inactive > 6 months and response < 10%, heavily penalize (0.5).
    If highly active and responsive, boost (1.2).
    """
    signals = candidate.get("redrob_signals", {})
    response_rate = signals.get("recruiter_response_rate", 0)
    
    try:
        last_active = datetime.strptime(signals.get("last_active_date", "1970-01-01"), "%Y-%m-%d")
        months_inactive = (datetime(2026, 6, 1) - last_active).days / 30.0
    except:
        months_inactive = 12
        
    multiplier = 1.0
    
    # Penalize low engagement
    if months_inactive > 6 and response_rate < 0.1:
        multiplier = 0.5
    # Boost high engagement
    elif months_inactive < 3 and response_rate > 0.6:
        multiplier = 1.2
        
    return multiplier

JD_TEXT = """
Job Description: Senior AI Engineer — Founding Team
Company: Redrob AI (Series A AI-native talent intelligence platform)
Location: Pune/Noida, India (Hybrid — flexible cadence) | Open to relocation candidates from Tier-1 Indian cities
Employment Type: Full-time
Experience Required: 5–9 years

Deep technical depth in modern ML systems — embeddings, retrieval, ranking, LLMs, fine-tuning.
Scrappy product-engineering attitude — willing to ship a working ranker in a week even if the underlying ML is "obviously suboptimal," because we need to learn from real users before we know what to actually optimize for.
Production experience with embeddings-based retrieval systems (sentence-transformers, OpenAI embeddings, BGE, E5, or similar) deployed to real users.
Production experience with vector databases or hybrid search infrastructure — Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS.
Strong Python. Yes really, we care about code quality.
Hands-on experience designing evaluation frameworks for ranking systems — NDCG, MRR, MAP, offline-to-online correlation, A/B test interpretation.
"""

def main():
    candidates = load_and_filter_candidates(DATA_PATH)
    
    processed_data = []
    texts_to_embed = []
    
    print("Extracting features and multipliers...")
    for c in candidates:
        text = extract_text_features(c)
        mult = calculate_behavioral_multiplier(c)
        
        processed_data.append({
            "candidate_id": c.get("candidate_id"),
            "multiplier": mult,
            "raw_text": text,
            "profile": c.get("profile", {})
        })
        texts_to_embed.append(text)
        
    if SentenceTransformer is None:
        print("sentence-transformers not installed. Skipping embedding generation.")
        return
        
    print("Loading embedding model (this may download weights on first run)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("Generating candidate embeddings (this will take some time)...")
    embeddings = model.encode(texts_to_embed, show_progress_bar=True, convert_to_numpy=True)
    
    for i, data in enumerate(processed_data):
        data["embedding"] = embeddings[i]
        
    print("Generating JD embedding...")
    jd_embedding = model.encode(JD_TEXT, convert_to_numpy=True)
        
    # Save both candidates and JD embedding
    save_payload = {
        "jd_embedding": jd_embedding,
        "candidates": processed_data
    }
        
    print(f"Saving {len(processed_data)} records + JD embedding to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(save_payload, f)
        
    print("Offline pre-processing complete!")

if __name__ == "__main__":
    main()
