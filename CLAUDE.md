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
├── qa-agent.mjs      # Custom QA Agent (Claude + GitHub API)
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

## QA Agent (qa-agent.mjs)
- **Purpose:** AI-powered QA agent that reviews PRs, analyzes repo health, and posts review comments
- **Stack:** Claude Opus 4.6 (Anthropic SDK) + GitHub API (via `gh` CLI)
- **Tools:** 10 GitHub tools (list PRs, get diffs, search code, post reviews, etc.)
- **GitHub Enterprise:** Set `GH_HOST` and `GITHUB_API_URL` for GitHub Enterprise Server
- **Usage:**
  ```bash
  # Review a specific PR
  ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --pr 42
  # Repo health check
  ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --health
  # General QA summary
  ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo
  # Actually post review comments
  ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --pr 42 --post-review
  ```

## Environment Variables
- `ANTHROPIC_API_KEY` — Claude API key (required for qa-agent)
- `GITHUB_PAT_TOKEN` — GitHub Personal Access Token (stored in `.env`, gitignored)
- `GITHUB_API_URL` — GitHub Enterprise API URL (optional, default: api.github.com)

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
