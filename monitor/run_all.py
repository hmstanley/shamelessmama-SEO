"""
Run all SEO monitors and update the dashboard.
This is the only script that needs to run daily.

Run: python monitor/run_all.py
Then open: dashboard/index.html in your browser

What each script does:
  site_audit.py      — checks meta tags, schema, page speed, directories
  seo_monitor.py     — checks keyword rankings on Yahoo/Bing
  internal_links.py  — finds blog posts missing internal links to service pages
  mention_scanner.py — finds web mentions of Marilyn that don't link back
  quoted_monitor.py  — reads Quoted digest emails, drafts expert responses
  content_brief.py   — generates AI blog briefs for keywords you haven't covered yet
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(__file__)


def run_script(script_name, optional=False):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"\n{'='*60}")
    print(f"Running {script_name}...")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    success = result.returncode == 0
    if not success and not optional:
        print(f"  ⚠️  {script_name} had errors — see above.")
    return success


if __name__ == "__main__":
    print("\n🌸 Shameless Mama Wellness — Daily SEO Check")
    print("This will take a few minutes. Please wait...\n")

    # Core checks (always run)
    ok1 = run_script("site_audit.py")
    ok2 = run_script("seo_monitor.py")
    ok3 = run_script("internal_links.py")

    # Outreach & content (needs internet + optionally Gmail / Anthropic API)
    ok4 = run_script("mention_scanner.py")
    ok5 = run_script("quoted_monitor.py", optional=True)   # needs Gmail config
    ok6 = run_script("content_brief.py",  optional=True)   # works best with API key

    print(f"\n{'='*60}")
    print("ALL DONE")
    print(f"{'='*60}")
    print("\nResults summary:")
    print(f"  Site audit:       {'✅' if ok1 else '⚠️ '}")
    print(f"  Keyword rankings: {'✅' if ok2 else '⚠️ '}")
    print(f"  Internal links:   {'✅' if ok3 else '⚠️ '}")
    print(f"  Mention scanner:  {'✅' if ok4 else '⚠️ '}")
    print(f"  Quoted monitor:   {'✅' if ok5 else '⚠️  (check Gmail config)'}")
    print(f"  Content briefs:   {'✅' if ok6 else '⚠️  (works best with API key)'}")
    print("\nNext step: Open dashboard/index.html in your browser")
    print("(Double-click the file, or drag it into Chrome/Safari)\n")
