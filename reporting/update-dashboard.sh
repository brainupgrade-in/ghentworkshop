#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# update-dashboard.sh — Quick wrapper to regenerate the lab dashboard
#
# Usage:
#   ./update-dashboard.sh                  # Generate dashboard
#   ./update-dashboard.sh --seed           # Create tracking issues (first time)
#   ./update-dashboard.sh --auto-refresh   # Generate with auto-refresh
#   ./update-dashboard.sh --open           # Generate and open in browser
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$REPO_ROOT/docs"
OUTPUT="$DOCS_DIR/lab-dashboard.html"

cd "$SCRIPT_DIR"

# Load token from repo-root .env if not already exported
if [ -z "${GITHUB_TOKEN:-}" ] && [ -z "${GITHUB_PAT_TOKEN:-}" ]; then
    if [ -f "$REPO_ROOT/.env" ]; then
        # shellcheck disable=SC1091
        set -a; source "$REPO_ROOT/.env"; set +a
        export GITHUB_TOKEN="${GITHUB_PAT_TOKEN:-${GITHUB_TOKEN:-}}"
    fi
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "Error: GITHUB_TOKEN not set. Export it or add to .env"
    exit 1
fi

mkdir -p "$DOCS_DIR"

OPEN_BROWSER=false
EXTRA_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --open) OPEN_BROWSER=true ;;
        *)      EXTRA_ARGS+=("$arg") ;;
    esac
done

echo "═══════════════════════════════════════════"
echo "  Lab Dashboard — GitHub Enterprise Workshop"
echo "═══════════════════════════════════════════"
echo ""

python3 generate-dashboard.py --output "$OUTPUT" "${EXTRA_ARGS[@]}"

echo ""
echo "  Dashboard: file://$OUTPUT"
echo "  GitHub Pages: https://brainupgrade-in.github.io/ghentworkshop/lab-dashboard.html"

if $OPEN_BROWSER; then
    if command -v xdg-open &>/dev/null; then
        xdg-open "$OUTPUT"
    elif command -v open &>/dev/null; then
        open "$OUTPUT"
    fi
fi
