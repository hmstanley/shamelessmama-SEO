#!/bin/bash
# ─────────────────────────────────────────────────────────────
# build-app.sh
# Creates "SEO Dashboard.app" on your Desktop using AppleScript.
# AppleScript apps are trusted by macOS without code signing.
#
# Usage (from inside the shamelessmama-SEO repo folder):
#   bash app/build-app.sh
# ─────────────────────────────────────────────────────────────

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DEST="$HOME/Desktop/SEO Dashboard.app"

echo ""
echo "🌸 Building SEO Dashboard.app..."
echo "   Repo: ${REPO_DIR}"
echo ""

# Write the AppleScript source
APPLESCRIPT=$(cat << SCRIPT
-- SEO Dashboard launcher
-- Runs the Python monitor scripts then opens the dashboard in the browser.

set repoPath to "${REPO_DIR}"
set logFile to repoPath & "/app/run.log"

-- Notify user we're starting
display notification "Running daily check — this takes a few minutes..." with title "🌸 SEO Dashboard"

-- Kill any existing server on port 8080
do shell script "lsof -ti tcp:8080 | xargs kill -9 2>/dev/null; exit 0"

-- Run all monitor scripts
do shell script "cd " & quoted form of repoPath & " && python3 monitor/run_all.py > " & quoted form of logFile & " 2>&1; exit 0"

-- Start web server in background
do shell script "cd " & quoted form of repoPath & " && python3 -m http.server 8080 --directory dashboard >> " & quoted form of logFile & " 2>&1 &"

-- Small pause for server to start
delay 2

-- Open browser
open location "http://localhost:8080"

-- Done notification
display notification "Dashboard is ready! Check your browser." with title "🌸 SEO Dashboard"
SCRIPT
)

# Compile the AppleScript into a .app
osacompile -o "${APP_DEST}" -e "${APPLESCRIPT}"

if [ $? -eq 0 ]; then
  echo "✅ Created: ${APP_DEST}"
  echo ""
  echo "Marilyn can now double-click 'SEO Dashboard' on her Desktop."
  echo "macOS may ask for permission to control the computer the first time — click OK."
  echo ""
else
  echo "❌ Build failed. Try running manually:"
  echo "   osacompile -o ~/Desktop/SEO\\ Dashboard.app -e '...'"
fi
