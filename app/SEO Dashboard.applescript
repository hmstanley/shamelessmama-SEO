-- SEO Dashboard
-- Paste this into Script Editor, then File > Export > Application

-- ⚠️ UPDATE THIS LINE if the repo is in a different folder
set repoPath to (POSIX path of (path to home folder)) & "shamelessmama-SEO"

set logFile to repoPath & "/app/run.log"

-- Kill anything already on port 8080
do shell script "lsof -ti tcp:8080 | xargs kill -9 2>/dev/null; true"

-- Start web server immediately (use existing data from last run)
do shell script "/usr/bin/python3 -m http.server 8080 --directory " & quoted form of (repoPath & "/dashboard") & " > " & quoted form of logFile & " 2>&1 &"

delay 1

-- Open browser right away — shows existing data while update runs in background
open location "http://localhost:8080"

-- Now kick off the data update in the background (won't block)
do shell script "cd " & quoted form of repoPath & " && nohup /usr/bin/python3 monitor/run_all.py >> " & quoted form of logFile & " 2>&1 &"

-- Tell user what's happening
display notification "Dashboard open! Data is refreshing in the background — takes 2-3 min." with title "🌸 SEO Dashboard"
