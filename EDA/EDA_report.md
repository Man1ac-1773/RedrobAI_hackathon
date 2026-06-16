# Exploratory Data Analysis (EDA) Report - Candidate Dataset

**Total Candidates Analyzed**: 100000

## 1. Demographics & Distributions

### Top 15 Job Titles
- Business Analyst: 5833 (5.83%)
- HR Manager: 5830 (5.83%)
- Mechanical Engineer: 5791 (5.79%)
- Accountant: 5764 (5.76%)
- Project Manager: 5754 (5.75%)
- Customer Support: 5750 (5.75%)
- Operations Manager: 5744 (5.74%)
- Content Writer: 5727 (5.73%)
- Sales Executive: 5713 (5.71%)
- Civil Engineer: 5702 (5.70%)
- Graphic Designer: 5689 (5.69%)
- Marketing Manager: 5524 (5.52%)
- Software Engineer: 3450 (3.45%)
- Full Stack Developer: 2873 (2.87%)
- Cloud Engineer: 2836 (2.84%)

### Top 10 Industries
- IT Services: 29881 (29.88%)
- Software: 22417 (22.42%)
- Manufacturing: 22305 (22.30%)
- Conglomerate: 7571 (7.57%)
- Paper Products: 7467 (7.47%)
- Fintech: 2808 (2.81%)
- Food Delivery: 2514 (2.51%)
- E-commerce: 1529 (1.53%)
- Consulting: 1274 (1.27%)
- EdTech: 610 (0.61%)

## 2. Anomalies & Traps (Honeypots)

- **Expert skill with 0 months duration (Clear Honeypot)**: 21
- **Implausible YOE timeline (Career roles don't add up to claimed YOE)**: 25
- **Negative career duration**: 0

## 3. Keyword Stuffers

- **Non-tech roles with Advanced/Expert AI skills**: 3942
  *(These are likely 'Marketing Managers' or 'Accountants' claiming expertise in RAG, Fine-tuning LLMs, etc.)*

## 4. Behavioral Engagement (`redrob_signals`)

- **Low Engagement ('Perfect-on-paper' traps)**: 1128
  *(Candidates who haven't logged in for >6 months and have <10% recruiter response rate)*
- **High Engagement (Goldmine)**: 11800
  *(Candidates active recently with >60% recruiter response rate)*
