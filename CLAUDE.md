# CLAUDE.md — ghentworkshop

## Overview
Workshop repository for Ghent-based training/demo sessions. Currently in early setup phase.

## Project Structure
```
ghentworkshop/
├── .env              # Environment secrets (GitHub PAT, API keys) — NEVER commit
├── .gitignore        # Excludes .env and common artifacts
├── README.md         # Project readme
└── CLAUDE.md         # This file
```

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
