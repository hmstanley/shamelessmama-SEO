#!/bin/bash
# ─────────────────────────────────────────────────────────────
# build-app.sh
# Run this ONCE to create "SEO Dashboard.app" on your Desktop.
# After that, Marilyn just double-clicks the app every morning.
#
# Usage (from inside the shamelessmama-SEO repo folder):
#   bash app/build-app.sh
# ─────────────────────────────────────────────────────────────

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="SEO Dashboard"
APP_DEST="$HOME/Desktop/${APP_NAME}.app"
MACOS_DIR="${APP_DEST}/Contents/MacOS"
RES_DIR="${APP_DEST}/Contents/Resources"

echo ""
echo "🌸 Building ${APP_NAME}.app..."
echo "   Repo: ${REPO_DIR}"
echo "   App:  ${APP_DEST}"
echo ""

# ── Create bundle structure ───────────────────────────────────
mkdir -p "${MACOS_DIR}"
mkdir -p "${RES_DIR}"

# ── Info.plist ────────────────────────────────────────────────
cat > "${APP_DEST}/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleExecutable</key>
  <string>launcher</string>
  <key>CFBundleIdentifier</key>
  <string>com.shamelessmama.seodashboard</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSUIElement</key>
  <false/>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

# ── Main launcher script ──────────────────────────────────────
cat > "${MACOS_DIR}/launcher" << LAUNCHER
#!/bin/bash
# This is the script that runs when Marilyn double-clicks the app.

REPO="${REPO_DIR}"
PORT=8080
LOG="\${REPO}/app/run.log"

# ── Helper: show Mac notification ────────────────────────────
notify() {
  osascript -e "display notification \"\$2\" with title \"\$1\" sound name \"Glass\""
}

# ── Kill any previous server on this port ─────────────────────
lsof -ti tcp:\${PORT} | xargs kill -9 2>/dev/null || true

notify "🌸 SEO Dashboard" "Running daily check... this takes a few minutes."

# ── Run all monitor scripts ───────────────────────────────────
cd "\${REPO}"
python3 monitor/run_all.py > "\${LOG}" 2>&1
EXIT_CODE=\$?

if [ \$EXIT_CODE -ne 0 ]; then
  notify "SEO Dashboard" "⚠️ Some checks had errors. Opening dashboard anyway."
fi

# ── Start web server in background ───────────────────────────
python3 -m http.server \${PORT} --directory "\${REPO}/dashboard" >> "\${LOG}" 2>&1 &
SERVER_PID=\$!
echo \$SERVER_PID > "\${REPO}/app/server.pid"

# ── Wait a moment for server to start ────────────────────────
sleep 1

# ── Open dashboard in default browser ────────────────────────
open "http://localhost:\${PORT}"

notify "🌸 SEO Dashboard" "Done! Dashboard is open in your browser."

# ── Keep server alive for 4 hours then shut down ─────────────
sleep 14400
kill \$SERVER_PID 2>/dev/null || true
LAUNCHER

chmod +x "${MACOS_DIR}/launcher"

# ── Try to set a nice icon (flower emoji via sips if possible) ─
# Use the Automator icon as fallback — it's always present on Mac
AUTOMATOR_ICON="/System/Library/CoreServices/Automator.app/Contents/Resources/Automator.icns"
if [ -f "${AUTOMATOR_ICON}" ]; then
  cp "${AUTOMATOR_ICON}" "${RES_DIR}/appIcon.icns"
  # Update plist to reference icon
  /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string appIcon" \
    "${APP_DEST}/Contents/Info.plist" 2>/dev/null || true
fi

echo "✅ App created at: ${APP_DEST}"
echo ""
echo "Marilyn can now:"
echo "  • Double-click 'SEO Dashboard' on her Desktop"
echo "  • Wait 2-3 minutes while it runs"
echo "  • The dashboard will open automatically in her browser"
echo ""
echo "To rebuild after a git pull, just run this script again."
echo ""
