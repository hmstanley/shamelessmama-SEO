#!/bin/bash
# ─────────────────────────────────────────────────────────────
# SEO Dashboard — double-click this file to open the dashboard
# ─────────────────────────────────────────────────────────────

REPO="$HOME/shamelessmama-SEO"
LOG="$REPO/app/run.log"

mkdir -p "$REPO/app"

echo ""
echo "🌸 Shameless Mama Wellness — SEO Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Kill any old server on port 8080
lsof -ti tcp:8080 | xargs kill -9 2>/dev/null || true

# Start web server
python3 -m http.server 8080 --directory "$REPO/dashboard" > "$LOG" 2>&1 &
SERVER_PID=$!
sleep 1

# Open dashboard in browser immediately
open "http://localhost:8080"
echo "✅ Dashboard open in your browser!"
echo ""
echo "⏳ Now updating your data in the background..."
echo "   (This takes 2-3 minutes — you can close this window)"
echo ""

# Run monitor scripts in background
python3 "$REPO/monitor/run_all.py" >> "$LOG" 2>&1

echo ""
echo "✅ Data update complete! Refresh your browser to see new results."
echo ""
echo "   You can now close this window."
echo ""

# Keep window open so she can read it
read -p "Press Enter to close..."
