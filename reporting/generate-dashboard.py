#!/usr/bin/env python3
"""
Lab Assignment & Completion Dashboard Generator
GitHub Enterprise for the Modern SDLC — 5-Day Workshop

Tracks lab completions for 25 participants via GitHub Issues.
Each lab has a tracking issue labeled 'lab-tracking'.
Participants comment on the issue to mark completion.

Usage:
    python3 generate-dashboard.py [--output dashboard.html] [--auto-refresh]
    GITHUB_TOKEN=ghp_xxx python3 generate-dashboard.py
"""

import os
import sys
import re
import argparse
from datetime import datetime
from collections import defaultdict

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

# ── Repository Configuration ──────────────────────────────────────────
REPO_OWNER = "brainupgrade-in"
REPO_NAME = "ghentworkshop"

# ── Course Structure ──────────────────────────────────────────────────
# day_number: (day_theme, {lab_num: lab_short_title})
COURSE_STRUCTURE = {
    1: {
        "theme": "Foundation — Platform, Identity & Planning",
        "color": "#58a6ff",       # Blue
        "labs": {
            1:  "Git Workflow",
            2:  "Code Review",
            3:  "Project Management",
        }
    },
    2: {
        "theme": "Prompting, Copilot & Agentic AI",
        "color": "#3fb950",       # Green
        "labs": {
            4:  "Copilot Develop",
            5:  "Copilot Testing",
            6:  "Copilot Agent",
        }
    },
    3: {
        "theme": "Standards, Automation & Secure Cloud",
        "color": "#e3b341",       # Amber
        "labs": {
            7:  "Actions CI",
            8:  "GHCR Publish",
            9:  "Environments",
        }
    },
    4: {
        "theme": "Quality, Security & Metrics",
        "color": "#f85149",       # Red
        "labs": {
            10: "CodeQL",
            11: "Secret Scanning",
            12: "Dependabot",
            13: "DORA Metrics",
        }
    },
    5: {
        "theme": "Integrations, DevEx & AI Frontier",
        "color": "#bc8cff",       # Purple
        "labs": {
            14: "Integrations",
            15: "Codespaces",
            16: "Capstone",
        }
    },
}

TOTAL_LABS = sum(len(d["labs"]) for d in COURSE_STRUCTURE.values())
ALL_LAB_NUMS = sorted(lab for d in COURSE_STRUCTURE.values() for lab in d["labs"])

# Reverse lookup: lab_num → (day, title)
LAB_TO_DAY = {}
for day_num, day_info in COURSE_STRUCTURE.items():
    for lab_num, lab_title in day_info["labs"].items():
        LAB_TO_DAY[lab_num] = (day_num, lab_title)


# ── GitHub API ────────────────────────────────────────────────────────

def get_github_token():
    """Get GitHub token from environment or .env file."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT_TOKEN")
    if not token:
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GITHUB_PAT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip("'\"")
                        break
                    elif line.startswith("GITHUB_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip("'\"")
                        break
    if not token:
        print("Error: GITHUB_TOKEN not set. Export it or add to .env")
        sys.exit(1)
    return token


def api_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_lab_issues(token):
    """Fetch all issues labeled 'lab-tracking'."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    headers = api_headers(token)
    all_issues = []
    page = 1

    while True:
        params = {"state": "all", "labels": "lab-tracking", "per_page": 100, "page": page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"Error fetching issues: {resp.status_code} — {resp.text[:200]}")
            sys.exit(1)
        issues = resp.json()
        if not issues:
            break
        all_issues.extend(issues)
        page += 1

    return all_issues


def fetch_issue_comments(token, issue_number):
    """Fetch all comments for a specific issue."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}/comments"
    resp = requests.get(url, headers=api_headers(token), params={"per_page": 100})
    if resp.status_code != 200:
        return []
    return resp.json()


# ── Parsing ───────────────────────────────────────────────────────────

def parse_issue_title(title):
    """Extract lab number from issue title.

    Supported formats:
        'Lab 01 - Git Workflow'
        'Day 1 - Lab 01'
        'Lab 01'
    Returns lab_num (int) or None.
    """
    m = re.search(r'Lab\s+(\d+)', title, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def extract_participant_name(comment_body):
    """Extract participant name from structured comment.

    Expected patterns:
        **Participant:** Jane Doe (jane@example.com)
        **Participant:** Jane Doe
        **Name:** Jane Doe
    Falls back to None (caller will use GitHub username).
    """
    patterns = [
        r'\*\*(?:Participant|Name):\*\*\s+([^\(\n]+?)\s*\([^\)]+\)',
        r'\*\*(?:Participant|Name):\*\*\s+([^\n]+)',
    ]
    for pat in patterns:
        m = re.search(pat, comment_body)
        if m:
            return m.group(1).strip()
    return None


def is_completion_comment(comment_body):
    """Detect whether a comment signals lab completion."""
    lower = comment_body.lower()
    indicators = [
        r'✅', r'completed', r'\[x\].*done', r'done',
        r'finished', r'all checks passed', r'lab complete',
    ]
    return any(re.search(p, lower) for p in indicators)


# ── Data Assembly ─────────────────────────────────────────────────────

def build_completion_data(token, issues):
    """Build { participant: { lab_num: {issue_number, date} } }."""
    matrix = defaultdict(dict)

    for issue in issues:
        lab_num = parse_issue_title(issue.get("title", ""))
        if lab_num is None or lab_num not in LAB_TO_DAY:
            continue

        issue_number = issue["number"]
        comments = fetch_issue_comments(token, issue_number)

        for c in comments:
            author = c.get("user", {}).get("login", "")
            body = c.get("body", "")
            created = c.get("created_at", "")

            if author.endswith("[bot]"):
                continue

            if is_completion_comment(body):
                name = extract_participant_name(body) or author
                if lab_num not in matrix[name]:
                    matrix[name][lab_num] = {
                        "issue_number": issue_number,
                        "completed_date": created,
                    }

    return matrix


# ── HTML Generation ───────────────────────────────────────────────────

def generate_html_dashboard(completion_matrix, output_file, auto_refresh=False):
    participants = sorted(completion_matrix.keys())
    total_participants = len(participants)

    total_completions = sum(len(labs) for labs in completion_matrix.values())
    overall_progress = (
        (total_completions / (TOTAL_LABS * total_participants) * 100)
        if total_participants > 0 else 0
    )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Start HTML ────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lab Completion Dashboard — GitHub Enterprise Workshop</title>
{"<meta http-equiv='refresh' content='60'>" if auto_refresh else ""}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}

body{{
  font-family:'JetBrains Mono',-apple-system,BlinkMacSystemFont,monospace;
  background:#070b13;
  color:#e6edf3;
  min-height:100vh;
  padding:20px;
}}
body::before{{
  content:'';position:fixed;inset:0;
  background-image:radial-gradient(circle,#1a2030 1px,transparent 1px);
  background-size:32px 32px;opacity:.35;pointer-events:none;z-index:0;
}}

.container{{max-width:1500px;margin:0 auto;position:relative;z-index:1}}

/* ── Header ───────────────────────────────────────────── */
.header{{
  background:linear-gradient(135deg,#0d1117 0%,#161b22 100%);
  border:1px solid #21262d;
  border-radius:12px;padding:30px;margin-bottom:20px;
  position:relative;
}}
.header h1{{
  font-family:'Syne',sans-serif;font-weight:800;font-size:1.8em;
  background:linear-gradient(90deg,#58a6ff,#bc8cff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  margin-bottom:6px;
}}
.header .subtitle{{color:#7d8590;font-size:.95em}}
.header .last-updated{{color:#484f58;font-size:.8em;margin-top:8px}}

.refresh-btn{{
  position:absolute;top:30px;right:30px;
  background:linear-gradient(135deg,#238636,#1f6feb);
  color:#fff;border:none;padding:10px 22px;border-radius:8px;
  font-size:.85em;font-weight:600;cursor:pointer;
  font-family:'JetBrains Mono',monospace;
  display:flex;align-items:center;gap:8px;
  transition:all .3s ease;
}}
.refresh-btn:hover{{transform:translateY(-2px);box-shadow:0 4px 12px rgba(63,185,80,.25)}}
.refresh-btn.refreshing{{opacity:.6;cursor:not-allowed}}
.refresh-btn.refreshing .refresh-icon{{animation:spin 1s linear infinite}}
@keyframes spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}

/* ── Stats Grid ───────────────────────────────────────── */
.stats-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:16px;margin-bottom:20px;
}}
.stat-card{{
  background:#0d1117;border:1px solid #21262d;
  border-radius:10px;padding:22px;
}}
.stat-card .label{{
  color:#7d8590;font-size:.75em;text-transform:uppercase;
  letter-spacing:.08em;margin-bottom:8px;
}}
.stat-card .value{{font-size:2.2em;font-weight:700;color:#e6edf3}}
.stat-card .sub-value{{color:#484f58;font-size:.8em;margin-top:4px}}

.stat-card.progress-card{{
  background:linear-gradient(135deg,#1f6feb,#8957e5);
  border-color:transparent;
}}
.stat-card.progress-card .label,
.stat-card.progress-card .value,
.stat-card.progress-card .sub-value{{color:#fff}}

.progress-bar{{
  background:rgba(255,255,255,.2);height:8px;border-radius:4px;
  margin-top:12px;overflow:hidden;
}}
.progress-bar-fill{{
  background:#fff;height:100%;border-radius:4px;
  transition:width .4s ease;
}}

/* ── Sections ─────────────────────────────────────────── */
.section{{
  background:#0d1117;border:1px solid #21262d;
  border-radius:12px;padding:28px;margin-bottom:20px;
}}
.section h2{{
  font-family:'Syne',sans-serif;font-weight:700;font-size:1.3em;
  margin-bottom:18px;padding-bottom:10px;
  border-bottom:1px solid #21262d;color:#e6edf3;
}}

/* ── Filters ──────────────────────────────────────────── */
.filter-container{{display:flex;align-items:center;gap:14px;margin-bottom:18px;flex-wrap:wrap}}
.filter-wrapper{{position:relative;flex:1;max-width:400px}}
.filter-icon{{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#484f58;font-size:1em}}
.filter-input{{
  width:100%;padding:10px 14px 10px 36px;
  background:#161b22;border:1px solid #30363d;border-radius:6px;
  color:#e6edf3;font-family:'JetBrains Mono',monospace;font-size:.85em;
  transition:border-color .2s;
}}
.filter-input:focus{{outline:none;border-color:#58a6ff;box-shadow:0 0 0 3px rgba(88,166,255,.1)}}
.filter-input::placeholder{{color:#484f58}}
.filter-clear{{
  position:absolute;right:10px;top:50%;transform:translateY(-50%);
  background:none;border:none;color:#484f58;cursor:pointer;
  font-size:1.1em;padding:4px;display:none;
}}
.filter-clear:hover{{color:#7d8590}}
.filter-clear.visible{{display:block}}
.filter-stats{{color:#7d8590;font-size:.8em;padding:6px 14px;background:#161b22;border-radius:6px;border:1px solid #21262d}}
.filter-stats strong{{color:#e6edf3}}

tr.hidden,.day-section.hidden{{display:none}}

/* ── Tables ───────────────────────────────────────────── */
.matrix-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:.82em}}
th{{
  background:#161b22;color:#7d8590;font-weight:600;
  padding:10px 8px;text-align:left;
  position:sticky;top:0;z-index:2;
  border-bottom:1px solid #30363d;
}}
td{{padding:9px 8px;border-bottom:1px solid #21262d}}
tr:hover td{{background:#161b22}}

.participant-name{{font-weight:600;color:#e6edf3;white-space:nowrap}}

/* Day header columns */
.day-col-header{{text-align:center;font-size:.7em;letter-spacing:.08em;text-transform:uppercase}}

/* Lab cells */
.lab-cell{{text-align:center;font-size:.9em}}
.lab-done{{color:#3fb950}}
.lab-pending{{color:#30363d}}

/* Status badges */
.status-badge{{
  display:inline-block;padding:3px 10px;border-radius:10px;
  font-size:.8em;font-weight:600;
}}
.status-complete{{background:rgba(63,185,80,.15);color:#3fb950;border:1px solid rgba(63,185,80,.3)}}
.status-partial{{background:rgba(227,179,65,.12);color:#e3b341;border:1px solid rgba(227,179,65,.3)}}
.status-none{{background:rgba(248,81,73,.12);color:#f85149;border:1px solid rgba(248,81,73,.3)}}

/* ── Day Sections ─────────────────────────────────────── */
.day-header{{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:14px;
}}
.day-title{{
  font-family:'Syne',sans-serif;font-weight:700;font-size:1.1em;
  display:flex;align-items:center;gap:10px;
}}
.day-dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
.day-progress{{display:flex;align-items:center;gap:10px}}
.day-progress-bar{{
  width:180px;background:#21262d;height:6px;border-radius:3px;overflow:hidden;
}}
.day-progress-fill{{height:100%;border-radius:3px;transition:width .3s ease}}
.day-progress-text{{font-size:.8em;color:#7d8590;min-width:55px;text-align:right}}

.day-section{{margin-bottom:28px}}
.day-section:last-child{{margin-bottom:0}}

/* ── Footer ───────────────────────────────────────────── */
.dashboard-footer{{
  text-align:center;padding:20px;color:#484f58;font-size:.75em;
  border-top:1px solid #21262d;margin-top:10px;
}}
.dashboard-footer a{{color:#58a6ff;text-decoration:none}}
.dashboard-footer a:hover{{text-decoration:underline}}

/* ── Responsive ───────────────────────────────────────── */
@media(max-width:768px){{
  .stats-grid{{grid-template-columns:1fr 1fr}}
  .day-progress-bar{{width:100px}}
  .refresh-btn{{position:static;margin-top:14px}}
}}
@media(max-width:480px){{
  .stats-grid{{grid-template-columns:1fr}}
}}

/* ── No-results ───────────────────────────────────────── */
.no-results{{text-align:center;padding:40px;color:#484f58;font-size:1em}}
.no-results-icon{{font-size:2.5em;margin-bottom:8px;opacity:.5}}
</style>
</head>
<body>
<div class="container">

<!-- ── Header ──────────────────────────────────────────── -->
<div class="header">
  <button class="refresh-btn" onclick="refreshDashboard()">
    <span class="refresh-icon">&#x21bb;</span><span>Refresh</span>
  </button>
  <h1>Lab Completion Dashboard</h1>
  <div class="subtitle">GitHub Enterprise for the Modern SDLC &mdash; 5-Day Workshop</div>
  <div class="last-updated">Last updated: {now_str}</div>
</div>

<!-- ── Stats ───────────────────────────────────────────── -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="label">Participants</div>
    <div class="value">{total_participants}</div>
    <div class="sub-value">Enrolled in workshop</div>
  </div>
  <div class="stat-card">
    <div class="label">Total Labs</div>
    <div class="value">{TOTAL_LABS}</div>
    <div class="sub-value">15 labs + 1 capstone &middot; 5 days</div>
  </div>
  <div class="stat-card">
    <div class="label">Completions</div>
    <div class="value">{total_completions}</div>
    <div class="sub-value">of {TOTAL_LABS * total_participants if total_participants else 0} possible</div>
  </div>
  <div class="stat-card progress-card">
    <div class="label">Overall Progress</div>
    <div class="value">{overall_progress:.1f}%</div>
    <div class="progress-bar"><div class="progress-bar-fill" style="width:{overall_progress:.1f}%"></div></div>
  </div>
</div>
"""

    # ── Completion Matrix ─────────────────────────────────
    html += f"""
<div class="section">
  <h2>Completion Matrix</h2>
  <div class="filter-container">
    <div class="filter-wrapper">
      <span class="filter-icon">&#x1F50D;</span>
      <input type="text" id="userFilter" class="filter-input" placeholder="Filter by participant name...">
      <button class="filter-clear" id="userFilterClear" onclick="clearUserFilter()">&times;</button>
    </div>
    <div class="filter-stats">
      Showing <strong id="visibleUsers">{len(participants)}</strong> of <strong>{len(participants)}</strong> participants
    </div>
  </div>
  <div class="matrix-wrap">
    <table id="completionTable">
      <thead>
        <tr>
          <th rowspan="2" style="vertical-align:bottom">Participant</th>
"""

    # Day group headers
    for day_num, day_info in COURSE_STRUCTURE.items():
        n = len(day_info["labs"])
        color = day_info["color"]
        html += f'          <th colspan="{n}" class="day-col-header" style="color:{color};border-bottom:2px solid {color}">Day {day_num}</th>\n'

    html += '          <th rowspan="2" style="vertical-align:bottom">Total</th>\n'
    html += '          <th rowspan="2" style="vertical-align:bottom">Status</th>\n'
    html += "        </tr>\n        <tr>\n"

    # Lab sub-headers
    for day_num, day_info in COURSE_STRUCTURE.items():
        color = day_info["color"]
        for lab_num, lab_title in day_info["labs"].items():
            html += f'          <th style="text-align:center;font-size:.7em;color:{color}" title="Lab {lab_num:02d}: {lab_title}">L{lab_num:02d}</th>\n'

    html += "        </tr>\n      </thead>\n      <tbody>\n"

    if not participants:
        html += f'        <tr><td colspan="{TOTAL_LABS + 3}" class="no-results"><div class="no-results-icon">&#x1F4CB;</div>No submissions yet. Waiting for participants...</td></tr>\n'
    else:
        for participant in participants:
            labs = completion_matrix[participant]
            total_done = len(labs)
            pct = (total_done / TOTAL_LABS * 100) if TOTAL_LABS else 0

            html += f'        <tr>\n          <td class="participant-name">{participant}</td>\n'

            for lab_num in ALL_LAB_NUMS:
                if lab_num in labs:
                    html += '          <td class="lab-cell lab-done" title="Completed">&#x2705;</td>\n'
                else:
                    html += '          <td class="lab-cell lab-pending">&mdash;</td>\n'

            status_cls = "status-complete" if pct >= 90 else "status-partial" if pct >= 50 else "status-none"
            html += f'          <td style="text-align:center"><strong>{total_done}/{TOTAL_LABS}</strong></td>\n'
            html += f'          <td style="text-align:center"><span class="status-badge {status_cls}">{pct:.0f}%</span></td>\n'
            html += "        </tr>\n"

    html += "      </tbody>\n    </table>\n  </div>\n</div>\n"

    # ── Day Details ───────────────────────────────────────
    html += """
<div class="section">
  <h2>Day-by-Day Breakdown</h2>
  <div class="filter-container">
    <div class="filter-wrapper">
      <span class="filter-icon">&#x1F50D;</span>
      <input type="text" id="dayFilter" class="filter-input" placeholder="Filter by day or lab name...">
      <button class="filter-clear" id="dayFilterClear" onclick="clearDayFilter()">&times;</button>
    </div>
    <div class="filter-stats">
      Showing <strong id="visibleDays">5</strong> of <strong>5</strong> days
    </div>
  </div>
"""

    for day_num, day_info in COURSE_STRUCTURE.items():
        color = day_info["color"]
        labs = day_info["labs"]
        n_labs = len(labs)

        # Day completion stats
        day_completions = 0
        for p in participants:
            for lab_num in labs:
                if lab_num in completion_matrix[p]:
                    day_completions += 1

        day_total = n_labs * total_participants if total_participants else n_labs
        day_pct = (day_completions / day_total * 100) if day_total else 0

        html += f"""
  <div class="day-section" data-day="{day_num}">
    <div class="day-header">
      <div class="day-title">
        <span class="day-dot" style="background:{color}"></span>
        Day {day_num}: {day_info["theme"]}
      </div>
      <div class="day-progress">
        <div class="day-progress-bar">
          <div class="day-progress-fill" style="width:{day_pct:.1f}%;background:{color}"></div>
        </div>
        <div class="day-progress-text">{day_completions}/{day_total}</div>
      </div>
    </div>
"""

        if participants:
            html += "    <table>\n      <thead><tr><th>Participant</th>\n"
            for lab_num, lab_title in labs.items():
                html += f'        <th style="text-align:center;color:{color}" title="{lab_title}">Lab {lab_num:02d}<br><span style="font-size:.75em;font-weight:400;color:#7d8590">{lab_title}</span></th>\n'
            html += "      </tr></thead>\n      <tbody>\n"

            for participant in participants:
                html += f'      <tr><td class="participant-name">{participant}</td>\n'
                for lab_num in labs:
                    if lab_num in completion_matrix[participant]:
                        date_str = completion_matrix[participant][lab_num].get("completed_date", "")
                        short_date = date_str[:10] if date_str else ""
                        html += f'        <td class="lab-cell lab-done" title="Completed {short_date}">&#x2705;</td>\n'
                    else:
                        html += '        <td class="lab-cell lab-pending">&mdash;</td>\n'
                html += "      </tr>\n"

            html += "      </tbody>\n    </table>\n"
        else:
            html += '    <p style="color:#484f58;text-align:center;padding:20px">No submissions yet</p>\n'

        html += "  </div>\n"

    html += "</div>\n"

    # ── Footer ────────────────────────────────────────────
    html += f"""
<div class="dashboard-footer">
  &copy; 2026 gheWARE &middot; <a href="https://devops.gheware.com">devops.gheware.com</a>
  &middot; Generated {now_str}
</div>

</div><!-- /container -->

<script>
function refreshDashboard(){{
  const btn=document.querySelector('.refresh-btn');
  btn.classList.add('refreshing');btn.disabled=true;
  btn.querySelector('span:last-child').textContent='Refreshing...';
  setTimeout(()=>window.location.reload(),300);
}}

/* ── Participant Filter (Completion Matrix) ─── */
function filterUsers(){{
  const f=document.getElementById('userFilter').value.toLowerCase();
  const rows=document.getElementById('completionTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
  const clr=document.getElementById('userFilterClear');
  let vis=0;
  for(let i=0;i<rows.length;i++){{
    const c=rows[i].getElementsByClassName('participant-name')[0];
    if(c&&(c.textContent||c.innerText).toLowerCase().indexOf(f)>-1){{
      rows[i].classList.remove('hidden');vis++;
    }}else{{ rows[i].classList.add('hidden'); }}
  }}
  document.getElementById('visibleUsers').textContent=vis;
  f?clr.classList.add('visible'):clr.classList.remove('visible');
}}
function clearUserFilter(){{
  document.getElementById('userFilter').value='';filterUsers();
  document.getElementById('userFilter').focus();
}}

/* ── Day Filter (Day Breakdown) ────────────── */
function filterDays(){{
  const f=document.getElementById('dayFilter').value.toLowerCase();
  const secs=document.getElementsByClassName('day-section');
  const clr=document.getElementById('dayFilterClear');
  let vis=0;
  for(let i=0;i<secs.length;i++){{
    const t=secs[i].textContent.toLowerCase();
    if(t.indexOf(f)>-1){{ secs[i].classList.remove('hidden');vis++; }}
    else{{ secs[i].classList.add('hidden'); }}
  }}
  document.getElementById('visibleDays').textContent=vis;
  f?clr.classList.add('visible'):clr.classList.remove('visible');
}}
function clearDayFilter(){{
  document.getElementById('dayFilter').value='';filterDays();
  document.getElementById('dayFilter').focus();
}}

/* ── Init ──────────────────────────────────── */
document.addEventListener('DOMContentLoaded',()=>{{
  document.getElementById('userFilter').addEventListener('input',filterUsers);
  document.getElementById('dayFilter').addEventListener('input',filterDays);
  document.getElementById('userFilter').addEventListener('keydown',e=>{{if(e.key==='Escape')clearUserFilter()}});
  document.getElementById('dayFilter').addEventListener('keydown',e=>{{if(e.key==='Escape')clearDayFilter()}});
}});

document.addEventListener('keydown',e=>{{
  if((e.ctrlKey||e.metaKey)&&e.shiftKey&&e.key==='R'){{ e.preventDefault();refreshDashboard(); }}
  if((e.ctrlKey||e.metaKey)&&e.key==='f'){{ e.preventDefault();document.getElementById('userFilter').focus(); }}
}});
</script>
</body>
</html>
"""

    with open(output_file, "w") as f:
        f.write(html)

    print(f"  Dashboard generated: {output_file}")
    print(f"  Open in browser: file://{os.path.abspath(output_file)}")


# ── Seed Issues ───────────────────────────────────────────────────────

def seed_tracking_issues(token):
    """Create one GitHub issue per lab, labeled 'lab-tracking'.

    Idempotent: skips labs that already have a tracking issue.
    """
    existing = fetch_lab_issues(token)
    existing_labs = set()
    for issue in existing:
        lab = parse_issue_title(issue.get("title", ""))
        if lab is not None:
            existing_labs.add(lab)

    headers = api_headers(token)
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"

    # Ensure label exists
    label_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/labels"
    resp = requests.get(label_url, headers=headers)
    label_names = [l["name"] for l in resp.json()] if resp.status_code == 200 else []
    if "lab-tracking" not in label_names:
        requests.post(label_url, headers=headers, json={
            "name": "lab-tracking",
            "color": "1f6feb",
            "description": "Lab completion tracking issue",
        })
        print("  Created label: lab-tracking")

    created = 0
    for day_num, day_info in COURSE_STRUCTURE.items():
        for lab_num, lab_title in day_info["labs"].items():
            if lab_num in existing_labs:
                print(f"  Lab {lab_num:02d} already exists, skipping")
                continue

            is_capstone = lab_num == 16
            title = f"Lab {lab_num:02d} — {lab_title}" + (" (Capstone)" if is_capstone else "")
            body = f"""## Lab {lab_num:02d}: {lab_title}
**Day {day_num}** — {day_info['theme']}

### How to mark completion

Post a comment on this issue with:

```
**Participant:** Your Name (your.email@company.com)
✅ Completed
```

The dashboard will automatically pick up your submission.

### Validation checklist
_Refer to the lab page for the full checklist._
"""
            resp = requests.post(url, headers=headers, json={
                "title": title,
                "body": body,
                "labels": ["lab-tracking"],
            })
            if resp.status_code == 201:
                print(f"  Created: #{resp.json()['number']} — {title}")
                created += 1
            else:
                print(f"  Error creating Lab {lab_num:02d}: {resp.status_code}")

    print(f"\n  {created} issues created, {len(existing_labs)} already existed")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GitHub Enterprise Workshop — Lab Completion Dashboard"
    )
    default_output = os.path.join(os.path.dirname(__file__), "..", "docs", "lab-dashboard.html")
    parser.add_argument("--output", default=default_output, help="Output HTML file")
    parser.add_argument("--auto-refresh", action="store_true", help="Auto-refresh every 60s")
    parser.add_argument("--seed", action="store_true", help="Create tracking issues on GitHub (run once)")
    args = parser.parse_args()

    token = get_github_token()

    if args.seed:
        print("Seeding lab-tracking issues...")
        seed_tracking_issues(token)
        print()

    print("Fetching lab tracking data...")
    issues = fetch_lab_issues(token)
    print(f"  Found {len(issues)} lab-tracking issues")

    print("Processing completions...")
    matrix = build_completion_data(token, issues)
    print(f"  {len(matrix)} participants found")

    print("Generating dashboard...")
    generate_html_dashboard(matrix, args.output, args.auto_refresh)


if __name__ == "__main__":
    main()
