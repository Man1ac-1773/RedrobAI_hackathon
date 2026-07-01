# Candidate Dataset Audit

- Candidate records: **100,000**
- Dataset reference date inferred from activity: **2026-06-03**
- Direct target-role profiles: **160**
- Profiles failing at least one integrity check: **144**

## Most Common Titles

- Business Analyst: 5,833 (5.83%)
- HR Manager: 5,830 (5.83%)
- Mechanical Engineer: 5,791 (5.79%)
- Accountant: 5,764 (5.76%)
- Project Manager: 5,754 (5.75%)
- Customer Support: 5,750 (5.75%)
- Operations Manager: 5,744 (5.74%)
- Content Writer: 5,727 (5.73%)
- Sales Executive: 5,713 (5.71%)
- Civil Engineer: 5,702 (5.70%)
- Graphic Designer: 5,689 (5.69%)
- Marketing Manager: 5,524 (5.52%)
- Software Engineer: 3,450 (3.45%)
- Full Stack Developer: 2,873 (2.87%)
- Cloud Engineer: 2,836 (2.84%)
- Java Developer: 2,809 (2.81%)
- .NET Developer: 2,788 (2.79%)
- DevOps Engineer: 2,787 (2.79%)
- Mobile Developer: 2,757 (2.76%)
- Frontend Engineer: 2,738 (2.74%)

## Most Common Industries

- IT Services: 29,881 (29.88%)
- Software: 22,417 (22.42%)
- Manufacturing: 22,305 (22.30%)
- Conglomerate: 7,571 (7.57%)
- Paper Products: 7,467 (7.47%)
- Fintech: 2,808 (2.81%)
- Food Delivery: 2,514 (2.51%)
- E-commerce: 1,529 (1.53%)
- Consulting: 1,274 (1.27%)
- EdTech: 610 (0.61%)

## Integrity Findings

- claimed experience conflicts with the career timeline: 48
- employment at Krutrim predates the company: 38
- employment at Sarvam AI predates the company: 35
- profile and summary state contradictory experience: 27
- expert skills report zero usage duration: 21
- employment at Glance predates the company: 2
- employment at Rephrase.ai predates the company: 2

These checks are conservative consistency tests, not ground-truth labels. Any failing profile is held below score 5 by the ranker.

## Behavioral Availability

- Inactive over 180 days with under 10% response: 1,185
- Active within 90 days with over 60% response: 11,416

The ranking uses behavior as a modifier after technical relevance; high engagement cannot rescue an irrelevant profile.
