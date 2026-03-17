# CLAUDE.md — ghentworkshop

## Overview
Workshop repository for Ghent-based training/demo sessions demonstrating AI-powered DevOps with GitHub Enterprise Cloud. Features DORA metrics dashboards, a custom QA agent, and MCP server integrations.

## Project Structure
```
ghentworkshop/
├── .env                    # Secrets (GitHub PAT, Anthropic key) — NEVER commit
├── .gitignore              # Git exclusions
├── .claudeignore           # Claude context exclusions
├── dora-dashboard.html     # DORA Metrics Dashboard (self-contained HTML)
├── qa-agent.mjs            # Custom QA Agent (Claude + GitHub API)
├── package.json            # Node.js dependencies
├── README.md               # Project readme
└── CLAUDE.md               # This file
```

## GitHub Project Board
- **URL:** https://github.com/users/brainupgrade-in/projects/22
- **Custom fields:** Deploy Frequency, Lead Time, MTTR, Change Failure Rate, Team, Sprint, DORA Level
- **Data:** 30 issues (5 teams × 6 sprints) with realistic DORA trajectories
- **Insights:** https://github.com/users/brainupgrade-in/projects/22/insights

## DORA Metrics Dashboard
- **File:** `dora-dashboard.html` — open in browser, no build step
- **Metrics:** Deployment Frequency, Lead Time, MTTR, Change Failure Rate
- **Data:** Mock data for 5 teams over 26 weeks (Oct 2025 – Mar 2026)
- **Features:** Team filter, time range toggle, trend charts, team comparison, DORA level badges
- **Live:** https://brainupgrade-in.github.io/ghentworkshop/dora-dashboard.html

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
  # Actually post review comments (dry-run by default)
  ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --pr 42 --post-review
  ```

## Workshop Demo Plan — MCP + GitHub Enterprise Cloud

### Demo 1: AI PR Reviewer (Primary Demo)
```
Developer opens PR → MCP Server → Claude reviews code → Posts inline comments → Updates check status
```
- Show a PR with intentional issues (security flaw, missing tests, bad patterns)
- MCP server connects Claude to GitHub's PR API
- Claude reads diff, posts inline review comments in real-time
- **Files:** `mcp-github-server.mjs`, `pr-review-agent.mjs`

### Demo 2: DORA Metrics Dashboard
- GitHub Project board with custom fields tracking 4 DORA metrics
- Interactive HTML dashboard with trend charts and team comparison
- **Files:** `dora-dashboard.html`, GitHub Project #22

### Demo 3: Repo Health Check
- QA agent scans repo: CI/CD status, stale branches, security patterns, issue backlog
- Produces health report with A-F score and actionable recommendations
- **Command:** `node qa-agent.mjs --repo owner/repo --health`

### Top MCP Use Cases for GitHub Enterprise
| # | Use Case | Wow Factor | Enterprise Value |
|---|----------|-----------|-----------------|
| 1 | **AI PR Reviewer** — inline code review via MCP | High | High |
| 2 | **Incident Response Agent** — correlates commits, CI, PRs to root-cause | Very High | Very High |
| 3 | **Repo Migration Analyzer** — scans repos for upgrade readiness | Medium | Very High |
| 4 | **Security Scanner** — finds OWASP Top 10, hardcoded secrets | High | Very High |
| 5 | **Onboarding Agent** — generates codebase guides for new team members | Medium | High |

### MCP Architecture
```
┌──────────────────────────────────────────────────┐
│  GitHub Enterprise Cloud                          │
│  ┌──────────┐    Webhook     ┌────────────────┐  │
│  │  PR #42   │──────────────→│  MCP Server     │  │
│  │  (opened) │               │  (Node.js)      │  │
│  └──────────┘    ←───────────│                 │  │
│   AI review       GitHub API │  Claude API     │  │
│   comments                   │  + MCP Tools    │  │
│                              └────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Implementation Paths
| Approach | Pros | Cons |
|----------|------|------|
| **MCP Server + Claude Agent SDK** | Native MCP, built-in tools, clean | Needs Agent SDK |
| **GitHub Action + Claude API** | No infra, runs in GH runners | Less interactive |

## Environment Variables
- `ANTHROPIC_API_KEY` — Claude API key (required for qa-agent and MCP demos)
- `GITHUB_PAT_TOKEN` — GitHub Personal Access Token (stored in `.env`, gitignored)
- `GITHUB_API_URL` — GitHub Enterprise API URL (optional, default: api.github.com)
- `GH_HOST` — GitHub Enterprise hostname (for `gh` CLI)

## Security Rules
- **NEVER commit `.env` or any file containing secrets**
- Always verify `.gitignore` covers sensitive files before staging
- Use environment variables for all credentials
- `package.json` must not contain PAT tokens in repository URLs

## Development Commands
```bash
# Install dependencies
npm install

# Load environment
source .env

# Run QA agent
ANTHROPIC_API_KEY=sk-... node qa-agent.mjs --repo owner/repo --health

# Git workflow
git add -A && git status
git commit -m "description"
git push origin main
```

## Conventions
- Branch: `main` is the default branch
- Keep workshop materials self-contained in this repo
- Use `.env` for all secrets and API keys
- All demos should work with `node` + `gh` CLI — no extra infra
