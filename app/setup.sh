#!/bin/bash
# ─────────────────────────────────────────────────────────────
# setup.sh — First-time setup for shamelessmama-SEO
# Run this once after cloning the repo.
#
# Usage (from inside the shamelessmama-SEO repo folder):
#   bash app/setup.sh
# ─────────────────────────────────────────────────────────────

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "🌸 Shameless Mama Wellness — SEO Dashboard Setup"
echo "================================================="
echo ""

# ── Check Python 3 ────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 is not installed."
  echo "   Download it from: https://www.python.org/downloads/"
  echo "   (Choose the latest version and run the installer)"
  exit 1
fi
PYVER=$(python3 --version 2>&1)
echo "✅ Python found: ${PYVER}"

# ── Check for .serperAPI key ──────────────────────────────────
if [ -f "${REPO_DIR}/.serperAPI" ]; then
  KEY=$(cat "${REPO_DIR}/.serperAPI" | tr -d '[:space:]')
  if [ -n "${KEY}" ]; then
    echo "✅ Serper API key found"
  else
    echo "⚠️  .serperAPI file is empty — keyword rankings won't work"
    echo "   Get a free key at https://serper.dev and paste it into .serperAPI"
  fi
else
  echo ""
  echo "⚠️  No .serperAPI file found."
  echo "   To track Google keyword rankings, create a file called .serperAPI"
  echo "   in this folder with your API key from https://serper.dev"
  echo ""
fi

# ── Create data directory ─────────────────────────────────────
mkdir -p "${REPO_DIR}/dashboard/data"
mkdir -p "${REPO_DIR}/drafts/quoted"
mkdir -p "${REPO_DIR}/drafts/blog_briefs"
echo "✅ Data directories ready"

# ── Build the .app ────────────────────────────────────────────
echo ""
echo "Building SEO Dashboard.app on your Desktop..."
bash "${REPO_DIR}/app/build-app.sh"

echo "================================================="
echo "✅ Setup complete!"
echo ""
echo "What to do next:"
echo "  1. Double-click 'SEO Dashboard' on your Desktop"
echo "  2. Wait 2-3 minutes while it collects data"
echo "  3. The dashboard opens automatically in your browser"
echo ""
echo "After a git pull to get updates, just run:"
echo "  bash app/setup.sh"
echo ""
