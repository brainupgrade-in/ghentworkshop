# CLAUDE.md — ghentworkshop

## Overview
Workshop repository for Ghent-based training/demo sessions. Currently in early setup phase.

## Project Structure
```
ghentworkshop/
├── .env              # Environment secrets (GitHub PAT, API keys) — NEVER commit
├── .gitignore        # Excludes .env and common artifacts
├── .claudeignore     # Files excluded from Claude context
├── dora-dashboard.html  # DORA Metrics Dashboard (self-contained, open in browser)
├── README.md         # Project readme
└── CLAUDE.md         # This file
```

## DORA Metrics Dashboard
- **File:** `dora-dashboard.html` — single self-contained HTML file (Chart.js via CDN)
- **Usage:** Open in any browser — no build step or server needed
- **Metrics:** Deployment Frequency, Lead Time, MTTR, Change Failure Rate
- **Data:** Mock data for 5 teams over 26 weeks (Oct 2025 – Mar 2026) with seeded random noise
- **Features:** Team filter, time range toggle (3M/6M), trend charts, team comparison bar chart, performance summary table with DORA level badges (Elite/High/Medium/Low)
- **CDN deps:** Chart.js 4.x, chartjs-adapter-date-fns 3.x

## Environment Variables
- `GITHUB_PAT_TOKEN` — GitHub Personal Access Token (stored in `.env`, gitignored)

## Security Rules
- **NEVER commit `.env` or any file containing secrets**
- Always verify `.gitignore` covers sensitive files before staging
- Use environment variables for all credentials

## Development Commands
```bash
# Load environment
source .env

# Git workflow
git add -A && git status        # Always review before committing
git commit -m "description"
git push origin main
```

## Conventions
- Branch: `main` is the default branch
- Keep workshop materials self-contained in this repo
- Use `.env` for all secrets and API keys
