"""
R-Series OAuth Re-authorization Script
=======================================

Run this whenever the refresh token has been revoked (e.g. invalid_grant error)
or whenever you need to bootstrap access for a new store.

Usage
-----
    uv run scripts/reauthorize_rseries.py

The script will:
  1. Load credentials from the repo .env (or env vars)
  2. Print the Lightspeed authorization URL and open it in your browser
  3. Wait for you to paste back the redirect URL after approving
  4. Exchange the code for tokens
  5. Save the token to your chosen store (file or MySQL)

Environment variables read from .env
-------------------------------------
  LSR_CLIENT_ID       – your OAuth client ID
  LSR_CLIENT_SECRET   – your OAuth client secret
  LSR_REDIRECT_URI    – redirect URI registered for your app
                        (defaults to https://127.0.0.1/ — works for CLI-only apps
                        where Lightspeed redirects to localhost and you just paste
                        the resulting URL)
  LSR_SCOPE           – space-separated scopes (default: employee:all)

For file-based storage (local dev):
  LSR_TOKEN_FILE      – path to the JSON token file

For MySQL storage (production / bottlemover):
  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
  LSR_STORE_ID        – stores.id row to write the token into
"""

import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Make sure the src package is importable when run from the repo root
_repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(_repo_root / "src"))

from dotenv import load_dotenv

load_dotenv(_repo_root / ".env")

from pylightspeed.connection import FileTokenStore, MySQLTokenStore, RSeriesConnection

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

CLIENT_ID     = os.environ["LSR_CLIENT_ID"]
CLIENT_SECRET = os.environ["LSR_CLIENT_SECRET"]
REDIRECT_URI  = os.getenv("LSR_REDIRECT_URI", "https://127.0.0.1/")
SCOPE         = os.getenv("LSR_SCOPE", "employee:all")


# ---------------------------------------------------------------------------
# Choose token store
# ---------------------------------------------------------------------------

def _pick_store() -> "FileTokenStore | MySQLTokenStore":
    token_file = os.getenv("LSR_TOKEN_FILE")
    store_id   = os.getenv("LSR_STORE_ID")

    if token_file and store_id:
        print("\nBoth LSR_TOKEN_FILE and LSR_STORE_ID are set. Where should the token be saved?")
        print("  1. File  :", token_file)
        print("  2. MySQL : stores.id =", store_id)
        choice = input("Enter 1 or 2: ").strip()
        if choice == "2":
            return MySQLTokenStore(int(store_id))
        return FileTokenStore(token_file)

    if store_id:
        print(f"Using MySQL token store (stores.id = {store_id})")
        return MySQLTokenStore(int(store_id))

    if token_file:
        print(f"Using file token store: {token_file}")
        return FileTokenStore(token_file)

    # Neither set — prompt
    print("\nNo token store configured in .env.")
    print("  1. Save to a file")
    print("  2. Save to MySQL (stores table)")
    choice = input("Enter 1 or 2: ").strip()
    if choice == "2":
        store_id = input("Enter stores.id: ").strip()
        return MySQLTokenStore(int(store_id))
    token_file = input("Enter file path: ").strip()
    return FileTokenStore(token_file)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("R-Series OAuth Re-Authorization")
    print("=" * 60)
    print(f"  Client ID   : {CLIENT_ID[:12]}…")
    print(f"  Scope       : {SCOPE}")
    print(f"  Redirect URI: {REDIRECT_URI}")
    print()

    store = _pick_store()

    # Step 1 — build the authorization URL
    url, state, code_verifier = RSeriesConnection.get_authorization_url(
        CLIENT_ID, SCOPE, REDIRECT_URI
    )

    print("\nOpening Lightspeed authorization page in your browser…")
    print("If it doesn't open, paste this URL manually:\n")
    print(" ", url)
    print()
    webbrowser.open(url)

    # Step 2 — wait for the user to paste back the redirect URL
    print("After authorizing in the browser, Lightspeed will redirect you to:")
    print(f"  {REDIRECT_URI}?code=...&state=...")
    print()
    print("Copy the full address bar URL and paste it here.")
    redirected_url = input("Redirect URL: ").strip()

    # Parse the code and state out of the URL
    qs = parse_qs(urlparse(redirected_url).query)

    if "code" not in qs:
        print("\n✗ ERROR: No 'code' parameter found in the URL.")
        print("  Make sure you pasted the full redirect URL including the query string.")
        sys.exit(1)

    code = qs["code"][0]
    returned_state = qs.get("state", [None])[0]

    if returned_state != state:
        print(f"\n✗ ERROR: State mismatch (expected {state!r}, got {returned_state!r}).")
        print("  This may indicate a CSRF attack or a browser caching issue. Aborting.")
        sys.exit(1)

    print("\nExchanging authorization code for tokens…")

    # Step 3 — exchange the code
    token_data = RSeriesConnection.exchange_code_for_token(
        CLIENT_ID, CLIENT_SECRET, code, REDIRECT_URI,
        code_verifier=code_verifier,
    )

    # Step 4 — persist
    store.save(token_data)

    print(f"\n✓ Token saved to {store!r}")
    print(f"  access_token  : {token_data['access_token'][:16]}…")
    print(f"  refresh_token : {token_data['refresh_token'][:16]}…")
    print(f"  expires_in    : {token_data.get('expires_in', '?')}s")
    print()
    print("Re-authorization complete. Your connections should work again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
