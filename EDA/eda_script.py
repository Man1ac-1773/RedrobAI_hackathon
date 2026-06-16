import json
from collections import Counter, defaultdict
from datetime import datetime

file_path = "resources/[PUB] India_runs_data_and_ai_challenge/candidates.jsonl"
output_path = "docs/EDA_report.md"

total_candidates = 0
titles = Counter()
industries = Counter()

# Anomaly counters
expert_zero_months = 0
implausible_yoe_timeline = 0
negative_duration = 0
high_ai_skills_non_tech = 0
low_engagement = 0
high_engagement = 0

# Track AI keywords
ai_keywords = {"NLP", "Fine-tuning LLMs", "Image Classification", "RAG", "Pinecone", "Milvus", "Vector Database", "PyTorch", "Transformers", "LLMs", "LangChain"}

# Signals distributions
missing_signals = defaultdict(int)

print("Starting EDA...")

with open(file_path, "rt") as f:
    for line in f:
        total_candidates += 1
        candidate = json.loads(line)
        
        profile = candidate.get("profile", {})
        title = profile.get("current_title", "Unknown")
        titles[title] += 1
        industries[profile.get("current_industry", "Unknown")] += 1
        
        yoe = profile.get("years_of_experience", 0)
        
        # 1. Check for Honeypots
        # Rule 1: Expert proficiency with 0 months duration
        skills = candidate.get("skills", [])
        is_honeypot_1 = False
        for skill in skills:
            if skill.get("proficiency") == "expert" and skill.get("duration_months", -1) == 0:
                is_honeypot_1 = True
                break
        if is_honeypot_1:
            expert_zero_months += 1
            
        # Rule 2: Career duration mismatch with YOE
        career_history = candidate.get("career_history", [])
        total_career_months = sum(role.get("duration_months", 0) for role in career_history)
        if total_career_months / 12.0 < (yoe - 3): # Allowing some leeway
            implausible_yoe_timeline += 1
            
        # Rule 3: Negative duration
        if any(role.get("duration_months", 0) < 0 for role in career_history):
            negative_duration += 1
            
        # 2. Check for Keyword Stuffers
        is_non_tech = ("Manager" in title and "Engineering" not in title) or "Accountant" in title or "Support" in title or "Sales" in title or "Writer" in title
        has_advanced_ai = any(s.get("name") in ai_keywords and s.get("proficiency") in ["advanced", "expert"] for s in skills)
        if is_non_tech and has_advanced_ai:
            high_ai_skills_non_tech += 1
            
        # 3. Behavioral Engagement
        signals = candidate.get("redrob_signals", {})
        for k in ["last_active_date", "recruiter_response_rate"]:
            if k not in signals:
                missing_signals[k] += 1
                
        response_rate = signals.get("recruiter_response_rate", 0)
        try:
            last_active = datetime.strptime(signals.get("last_active_date", "1970-01-01"), "%Y-%m-%d")
            # If not logged in for 6 months (say before 2025-12-01 relative to dataset time ~mid 2026) and response rate < 0.1
            if last_active < datetime(2025, 12, 1) and response_rate < 0.1:
                low_engagement += 1
            if last_active > datetime(2026, 3, 1) and response_rate > 0.6:
                high_engagement += 1
        except Exception:
            pass

# Write EDA report
with open(output_path, "w") as f:
    f.write("# Exploratory Data Analysis (EDA) Report - Candidate Dataset\n\n")
    f.write(f"**Total Candidates Analyzed**: {total_candidates}\n\n")
    
    f.write("## 1. Demographics & Distributions\n\n")
    f.write("### Top 15 Job Titles\n")
    for t, c in titles.most_common(15):
        f.write(f"- {t}: {c} ({(c/total_candidates)*100:.2f}%)\n")
        
    f.write("\n### Top 10 Industries\n")
    for i, c in industries.most_common(10):
        f.write(f"- {i}: {c} ({(c/total_candidates)*100:.2f}%)\n")
        
    f.write("\n## 2. Anomalies & Traps (Honeypots)\n\n")
    f.write(f"- **Expert skill with 0 months duration (Clear Honeypot)**: {expert_zero_months}\n")
    f.write(f"- **Implausible YOE timeline (Career roles don't add up to claimed YOE)**: {implausible_yoe_timeline}\n")
    f.write(f"- **Negative career duration**: {negative_duration}\n")
    
    f.write("\n## 3. Keyword Stuffers\n\n")
    f.write(f"- **Non-tech roles with Advanced/Expert AI skills**: {high_ai_skills_non_tech}\n")
    f.write("  *(These are likely 'Marketing Managers' or 'Accountants' claiming expertise in RAG, Fine-tuning LLMs, etc.)*\n")
    
    f.write("\n## 4. Behavioral Engagement (`redrob_signals`)\n\n")
    f.write(f"- **Low Engagement ('Perfect-on-paper' traps)**: {low_engagement}\n")
    f.write("  *(Candidates who haven't logged in for >6 months and have <10% recruiter response rate)*\n")
    f.write(f"- **High Engagement (Goldmine)**: {high_engagement}\n")
    f.write("  *(Candidates active recently with >60% recruiter response rate)*\n")

print("EDA Complete. Report written to docs/EDA_report.md")
