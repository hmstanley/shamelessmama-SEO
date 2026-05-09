"""
One-time Google Search Console OAuth setup.
Run this once to authorize access and save a refresh token.

Run: python monitor/gsc_auth.py

It will open a browser, you log in as her Google account, click Allow,
and the refresh token is saved to ~/.shameless-gsc-token.json for future use.
"""

import json
import os
import urllib.request
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_FILE = os.path.expanduser("~/.shameless-gsc-client.json")
TOKEN_FILE = os.path.expanduser("~/.shameless-gsc-token.json")
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
REDIRECT_URI = "http://localhost:8765"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html><body style='font-family:sans-serif;padding:40px'>
            <h2>Authorization successful!</h2>
            <p>You can close this tab and return to the terminal.</p>
            </body></html>
        """)

    def log_message(self, format, *args):
        pass  # suppress server logs


def main():
    if not os.path.exists(CLIENT_FILE):
        print(f"Client secrets file not found: {CLIENT_FILE}")
        print("Download it from Google Cloud Console -> Credentials -> your OAuth client.")
        return

    with open(CLIENT_FILE) as f:
        client = json.load(f)["installed"]

    client_id = client["client_id"]
    client_secret = client["client_secret"]
    token_uri = client["token_uri"]

    # Build auth URL
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{params}"

    print("\nOpening browser for Google authorization...")
    print("Log in as her Google account and click Allow.\n")
    webbrowser.open(auth_url)

    # Wait for redirect
    server = HTTPServer(("localhost", 8765), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("Authorization failed — no code received.")
        return

    # Exchange code for tokens
    payload = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        token_uri,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        tokens = json.load(resp)

    if "refresh_token" not in tokens:
        print("No refresh token returned. Try deleting the app access at")
        print("https://myaccount.google.com/permissions and running again.")
        return

    # Save tokens
    save = {
        "client_id": client_id,
        "client_secret": client_secret,
        "token_uri": token_uri,
        "refresh_token": tokens["refresh_token"],
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(save, f, indent=2)

    print(f"Authorization successful!")
    print(f"Refresh token saved to {TOKEN_FILE}")
    print("\nYou're all set — the daily script will use this token automatically.")


if __name__ == "__main__":
    main()
