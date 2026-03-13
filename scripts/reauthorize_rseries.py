"""
R-Series OAuth Re-authorization Script
=======================================

Run this whenever the refresh token has been revoked (e.g. invalid_grant error)
or whenever you need to bootstrap access for a new store.

Usage
-----
    uv run scripts/reauthorize_rseries.py

The script will:
  1. Choose a token store (file, MySQL, or Vault)
  2. Load credentials from the store, falling back to env vars / .env
  3. Print the Lightspeed authorization URL and open it in your browser
  4. Wait for you to paste back the redirect URL after approving
  5. Exchange the code for tokens
  6. Save the token to the chosen store

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
  LSR_CREDENTIALS_FILE– (optional) path to a credentials JSON file

For MySQL storage:
  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
  LSR_STORE_ID        – stores.id row to write the token into
  LSR_CREDENTIALS_CONFIG_KEY – (optional) stores.config JSON key for credentials

For Vault storage:
  VAULT_ADDR                   – Vault server URL
  VAULT_TOKEN                  – Vault authentication token
  VAULT_LSR_TOKEN_PATH         – KV v2 path for the OAuth token (read + write)
  VAULT_LSR_CREDENTIALS_PATHS  – (optional) comma-separated list of KV v2 paths
                                 for static credentials, merged left-to-right
                                 (e.g. "lightspeed/shared,lightspeed/stores/2")
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

from pylightspeed.connection import FileTokenStore, StoresTableTokenStore, VaultTokenStore, RSeriesConnection

# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
# These are resolved after the store is chosen so that store.load_credentials()
# can supply them.  Populated in main() below.
CLIENT_ID = CLIENT_SECRET = REDIRECT_URI = SCOPE = None


# ---------------------------------------------------------------------------
# Choose token store
# ---------------------------------------------------------------------------

def _pick_store():
    token_file   = os.getenv("LSR_TOKEN_FILE")
    store_id     = os.getenv("LSR_STORE_ID")
    vault_token_path = os.getenv("VAULT_LSR_TOKEN_PATH")

    # Determine which backends are pre-configured
    configured = []
    if token_file:
        configured.append(("1", f"File          : {token_file}"))
    if store_id:
        configured.append(("2", f"MySQL         : stores.id = {store_id}"))
    if vault_token_path:
        configured.append(("3", f"Vault         : {vault_token_path}"))

    if len(configured) == 1:
        # Exactly one configured — use it without prompting
        key = configured[0][0]
    elif len(configured) > 1:
        print("\nMultiple token stores detected. Which should be used?")
        for key, label in configured:
            print(f"  {key}. {label}")
        key = input("Enter choice: ").strip()
    else:
        print("\nNo token store configured in .env. Choose one:")
        print("  1. File")
        print("  2. MySQL (stores table)")
        print("  3. Vault")
        key = input("Enter 1, 2, or 3: ").strip()

    if key == "1":
        if not token_file:
            token_file = input("Token file path: ").strip()
        creds_file = os.getenv("LSR_CREDENTIALS_FILE")
        print(f"Using file token store: {token_file}")
        return FileTokenStore(token_file, credentials_file=creds_file or None)

    if key == "2":
        if not store_id:
            store_id = input("stores.id: ").strip()
        creds_key = os.getenv("LSR_CREDENTIALS_CONFIG_KEY")
        print(f"Using MySQL token store (stores.id = {store_id})")
        return StoresTableTokenStore(int(store_id), credentials_config_key=creds_key or None)

    if key == "3":
        if not vault_token_path:
            vault_token_path = input("Vault KV path for token (e.g. lightspeed/stores/2): ").strip()
        raw_creds = os.getenv("VAULT_LSR_CREDENTIALS_PATHS") or input(
            "Vault KV path(s) for credentials, comma-separated (or blank to skip):\n"
            "  e.g. lightspeed/shared,lightspeed/stores/2\n> "
        ).strip() or None
        vault_creds = (
            [p.strip() for p in raw_creds.split(",") if p.strip()]
            if raw_creds
            else None
        )
        print(f"Using Vault token store: {vault_token_path}")
        return VaultTokenStore(
            vault_token_path,
            credentials_path=vault_creds,
        )

    print(f"Unknown choice {key!r}. Aborting.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("R-Series OAuth Re-Authorization")
    print("=" * 60)

    store = _pick_store()

    # Resolve credentials: store wins over .env, .env over missing
    store_creds = store.load_credentials() or {}
    client_id     = os.getenv("LSR_CLIENT_ID")     or store_creds.get("LSR_CLIENT_ID")
    client_secret = os.getenv("LSR_CLIENT_SECRET") or store_creds.get("LSR_CLIENT_SECRET")
    redirect_uri  = os.getenv("LSR_REDIRECT_URI")  or store_creds.get("LSR_REDIRECT_URI") or "https://127.0.0.1/"
    scope         = os.getenv("LSR_SCOPE")         or store_creds.get("LSR_SCOPE")        or "employee:all"

    if not client_id or not client_secret:
        raise SystemExit(
            "\n✗ LSR_CLIENT_ID and LSR_CLIENT_SECRET must be set in .env or provided "
            "by the token store's load_credentials()."
        )

    print(f"  Client ID   : {client_id[:12]}…")
    print(f"  Scope       : {scope}")
    print(f"  Redirect URI: {redirect_uri}")
    print()

    # Step 1 — build the authorization URL
    url, state, code_verifier = RSeriesConnection.get_authorization_url(
        client_id, scope, redirect_uri
    )

    print("\nOpening Lightspeed authorization page in your browser…")
    print("If it doesn't open, paste this URL manually:\n")
    print(" ", url)
    print()
    webbrowser.open(url)

    # Step 2 — wait for the user to paste back the redirect URL
    print("After authorizing in the browser, Lightspeed will redirect you to:")
    print(f"  {redirect_uri}?code=...&state=...")
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
        client_id, client_secret, code, redirect_uri,
        code_verifier=code_verifier,
    )

    # Step 4 — persist
    store.save_token(token_data)

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
