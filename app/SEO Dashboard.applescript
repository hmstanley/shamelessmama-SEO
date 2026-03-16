-- SEO Dashboard
-- Paste this into Script Editor, then File > Export > Application

-- Find the repo folder (same folder this script lives in, one level up)
set repoPath to (POSIX path of (path to home folder)) & "shamelessmama-SEO"

display notification "Running daily check — takes a few minutes..." with title "🌸 SEO Dashboard"

-- Kill anything already on port 8080
do shell script "lsof -ti tcp:8080 | xargs kill -9 2>/dev/null; true"

-- Run all monitor scripts
do shell script "/usr/bin/python3 " & quoted form of (repoPath & "/monitor/run_all.py") & " > " & quoted form of (repoPath & "/app/run.log") & " 2>&1; true"

-- Start local web server in background
do shell script "/usr/bin/python3 -m http.server 8080 --directory " & quoted form of (repoPath & "/dashboard") & " >> " & quoted form of (repoPath & "/app/run.log") & " 2>&1 &"

delay 2

-- Open in browser
open location "http://localhost:8080"

display notification "Dashboard is open in your browser!" with title "🌸 SEO Dashboard"
