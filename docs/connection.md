# Connections

pyLightspeed communicates with each Lightspeed series through a *connection* object. Every high-level `LightspeedXxxApi` class creates one automatically, so you normally never instantiate a connection directly — but understanding how they work is important when you need to do the initial OAuth setup or customise token storage.

## Authentication Styles

| Series | Authentication | Notes |
|--------|----------------|-------|
| **R-Series** (Retail) | OAuth 2.0 — Authorization Code Grant | Tokens stored via a `TokenStore`; automatically refreshed on expiry. |
| **X-Series** (Retail X) | OAuth 2.0 *or* Personal Access Token | OAuth tokens include an absolute `expires` timestamp and a per-retailer `domain_prefix`. Personal tokens are for Plus-plan retailers only. |
| **C-Series** (eCom) | HTTP Basic Auth (API key + secret) | No token management required. |
| **E-Series** (Ecwid) | API secret passed as a query parameter | No token management required. |

---

## R-Series (Lightspeed Retail)

R-Series uses OAuth 2.0. If you already have a token file from a previous authorisation you only need to point the API class at it. If you are setting up a **new** connection you will need to run the one-time authorization flow first.

### Using an Existing Token File

When a valid `codes.json` already exists, create the API instance and everything else is handled automatically — the library reads the refresh token, exchanges it for a fresh access token, and saves the updated token file.

```python
from pylightspeed.api import LightspeedRSeriesApi

lsr = LightspeedRSeriesApi(
    account_id="123456",
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_file="/path/to/codes.json",
)

# Start making API calls immediately
employees = lsr.Employee.listall()
```

### Using a Custom TokenStore

If you want to store tokens somewhere other than a local file (e.g. a database or secrets manager), pass a `TokenStore` instance. Implement `load` (returns a `dict` or `None`) and `save` (receives the full token `dict`).

```python
from pylightspeed.connection import TokenStore, FileTokenStore
from pylightspeed.api import LightspeedRSeriesApi

# Built-in file-based store (atomic writes, same as token_file= shorthand)
store = FileTokenStore("/path/to/codes.json")

# Custom store example
class EnvTokenStore(TokenStore):
    """Reads/writes tokens from environment variables (demo only)."""
    import os, json

    def load(self):
        raw = os.getenv("LS_TOKEN")
        return json.loads(raw) if raw else None

    def save(self, token_data):
        os.environ["LS_TOKEN"] = json.dumps(token_data)

lsr = LightspeedRSeriesApi(
    account_id="123456",
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_store=store,   # or token_store=EnvTokenStore()
)
```

### First-Time OAuth Setup (New Connection)

The first time you connect — or when the token file is missing — you need to run through the authorization flow once. This requires **browser and user interaction** (the store owner must approve your app), so it cannot happen automatically inside a server or container.

Run a one-off setup script from a machine with browser access:

```python
import webbrowser
from urllib.parse import urlparse, parse_qs

import requests
from pylightspeed.connection import RSeriesConnection, FileTokenStore

CLIENT_ID     = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI  = "https://127.0.0.1:5000/"   # must match your OAuth app settings
SCOPE         = "employee:all"
TOKEN_FILE    = "/path/to/codes.json"

# Step 1 — Build the authorization URL (PKCE enabled by default)
url, state, code_verifier = RSeriesConnection.get_authorization_url(
    CLIENT_ID, SCOPE, REDIRECT_URI
)

print("Opening authorization page in your browser…")
webbrowser.open(url)

# Step 2 — After the store owner approves, Lightspeed redirects to REDIRECT_URI
#           with ?code=...&state=... in the URL.
redirected_url = input("Paste the full redirect URL here: ")
code = parse_qs(urlparse(redirected_url).query)["code"][0]

# (Optional but recommended) Validate the returned state
returned_state = parse_qs(urlparse(redirected_url).query).get("state", [None])[0]
assert returned_state == state, "State mismatch — possible CSRF attack"

# Step 3 — Exchange the code for tokens
token_data = RSeriesConnection.exchange_code_for_token(
    CLIENT_ID, CLIENT_SECRET, code, REDIRECT_URI,
    code_verifier=code_verifier,   # required if PKCE was used
)

# Step 4 — Persist the tokens
FileTokenStore(TOKEN_FILE).save(token_data)
print("Token saved to", TOKEN_FILE)
```

!!! note
    `get_authorization_url()` generates PKCE parameters (S256 code challenge) by default.
    This is recommended by Lightspeed and required for publicly distributed clients.
    Pass `use_pkce=False` only when your OAuth app is registered as a non-PKCE client.

!!! warning
    The `code` received at your redirect URI is **valid for 60 seconds only**.
    Run the exchange step immediately after pasting the URL.

### Token File Format

The token file is plain JSON:

```json
{
    "access_token": "eyJ...",
    "expires_in": 3600,
    "token_type": "bearer",
    "scope": "employee:all",
    "refresh_token": "def502...",
    "last_run": 1740675432.1
}
```

`refresh_token` does **not** expire. The library always preserves it when saving updated tokens because Lightspeed does not return it in refresh responses.

---

## X-Series (Lightspeed Retail X)

X-Series supports two authentication methods.

### Personal Access Token

Suitable for single-store scripts run by a Plus-plan retailer.

```python
from pylightspeed.api import LightspeedXSeriesApi

lsx = LightspeedXSeriesApi(
    domain_prefix="mystore",     # "mystore" for mystore.retail.lightspeed.app
    personal_token="fMYg...",
)

products = lsx.Products.listall()
```

### OAuth (Multi-Store / Distributed App)

For applications that connect to multiple stores, use OAuth. Each retailer goes through the authorization flow once; their token (which includes their `domain_prefix`) is stored in a `TokenStore`.

**First-time setup for a new retailer:**

```python
import secrets, webbrowser
from urllib.parse import urlparse, parse_qs

from pylightspeed.connection import XSeriesOauthConnection, FileTokenStore

CLIENT_ID     = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI  = "https://yourapp.example.com/oauth/callback"
SCOPE         = "products:read sales:read customers:read"
TOKEN_FILE    = "/path/to/xseries_tokens.json"

# Step 1 — Build the authorization URL
state = secrets.token_urlsafe(12)   # at least 8 characters, required
url = XSeriesOauthConnection.get_authorization_url(
    CLIENT_ID, SCOPE, REDIRECT_URI, state
)

print("Send this URL to the retailer:", url)
webbrowser.open(url)

# Step 2 — Retailer approves; redirect URI receives ?code=...&domain_prefix=...&state=...
redirected_url = input("Paste the full redirect URL: ")
params = parse_qs(urlparse(redirected_url).query)
code          = params["code"][0]
domain_prefix = params["domain_prefix"][0]
returned_state = params.get("state", [None])[0]

assert returned_state == state, "State mismatch"

# Step 3 — Exchange code for tokens
token_data = XSeriesOauthConnection.exchange_code_for_token(
    CLIENT_ID, CLIENT_SECRET, code, REDIRECT_URI, domain_prefix
)

FileTokenStore(TOKEN_FILE).save(token_data)
```

**Using the connection after setup:**

```python
from pylightspeed.api import LightspeedXSeriesApi

lsx = LightspeedXSeriesApi(
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_file="/path/to/xseries_tokens.json",
)

sales = lsx.Sales.listall()
```

### X-Series Token Format

```json
{
    "access_token": "fMYg...",
    "token_type": "Bearer",
    "expires": 1740679032,
    "expires_in": 86400,
    "refresh_token": "J3F6...",
    "domain_prefix": "mystore",
    "scope": "products:read sales:read customers:read"
}
```

`expires` is an **absolute Unix timestamp**. The library refreshes the access token when fewer than 60 seconds remain. A new `refresh_token` is returned on every refresh — the library saves the latest value automatically.

---

## C-Series (Lightspeed eCom)

C-Series uses HTTP Basic Auth. No OAuth or token file required.

```python
from pylightspeed.api import LightspeedCSeriesApi

lsc = LightspeedCSeriesApi(
    api_key="your_api_key",
    api_secret="your_api_secret",
    # host defaults to "api.shoplightspeed.com"
    # api_path defaults to "/us/{}"  (change locale if needed)
)

products = lsc.Products.listall()
```

Obtain your API key and secret from the eCom back-office under **Apps → API credentials**.

---

## E-Series (Ecwid)

E-Series passes the API secret as a query parameter on every request.

```python
from pylightspeed.api import LightspeedESeriesApi

lse = LightspeedESeriesApi(
    store_id="12345678",
    api_secret="secret_your_ecwid_api_secret",
    # host defaults to "app.ecwid.com"
)

orders = lse.Orders.listall()
```

Use `api_public` instead of `api_secret` to use the store's public token (read-only access).

---

## Token Storage Reference

See the [connection API reference](reference/connection.md) for full class documentation on `TokenStore` and `FileTokenStore`.

---

## Errors

| Exception | When raised |
|-----------|-------------|
| `MissingTokenError` | No valid token found in the token store (token file missing, empty, or contains an `"error"` key). Run the OAuth setup flow. |
| `Unauthorised` | The API returned `401 Unauthorized`. Usually means the access token is invalid — re-run the OAuth setup flow and replace the token file. |
| `RateLimitingException` | The API returned `429 Too Many Requests`. The connection handles rate limiting automatically for R-Series (leaky bucket) and X-Series (`Retry-After` header), so this exception should be rare. |

---

## Connection API Reference

See the [connection API reference](reference/connection.md) for full class and method documentation for all connection classes.
