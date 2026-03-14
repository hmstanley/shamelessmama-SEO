"""
Run all SEO monitors and update the dashboard.
This is the only script that needs to run daily.

Run: python monitor/run_all.py
Then open: dashboard/index.html in your browser
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(__file__)


def run_script(script_name):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"\n{'='*60}")
    print(f"Running {script_name}...")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    return result.returncode == 0


if __name__ == "__main__":
    print("\n🌸 Shameless Mama Wellness — Daily SEO Check")
    print("This will take a few minutes. Please wait...\n")

    ok1 = run_script("site_audit.py")
    ok2 = run_script("seo_monitor.py")

    print(f"\n{'='*60}")
    print("ALL DONE")
    print(f"{'='*60}")
    print("\nNext step: Open dashboard/index.html in your browser")
    print("(Double-click the file, or drag it into Chrome/Safari)\n")

    if not ok1 or not ok2:
        print("⚠️  One or more checks had errors. Check output above.")
