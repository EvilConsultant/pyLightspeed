---
name: lightspeed-connection
description: >
  Create a new connection to a Lightspeed API (R-Series, C-Series, or X-Series)
  using pyLightspeed and a VaultTokenStore. Use this skill when wiring up a new
  app or store to Lightspeed, adding API access to an existing BottleManager app,
  setting up the per-store Vault path structure, or replacing a bare credential
  dict / token_file with the standard token store pattern.
---

# Creating Lightspeed Connections with pyLightspeed + Vault

## When to Use
- Connecting a new app or worker to a Lightspeed store
- Wiring up R-Series (Retail), C-Series (eCom), or X-Series for the first time
- Replacing `token_file=` / manual credential dicts with the Vault token store
- Setting up the Vault path structure for a store
- Debugging a `MissingCredentialsError` or `MissingTokenError`

---

## Vault Path Convention

All Lightspeed credentials follow this layout — never deviate from it:

| Vault path | Contents |
|---|---|
| `lightspeed/shared` | Shared R-Series OAuth app: `LSR_CLIENT_ID`, `LSR_CLIENT_SECRET`, and optionally `LSC_API_HOST`, `LSC_API_PATH` |
| `lightspeed/stores/{store_id}/creds` | Per-store static config: `LSR_ACCOUNT_ID`, `LSC_API_KEY`, `LSC_API_SECRET`, `LSX_PERSONAL_TOKEN`, etc. |
| `lightspeed/stores/{store_id}/token` | **Written automatically** by pyLightspeed on every OAuth token refresh. Do not pre-populate. |
| `lightspeed/stores/{store_id}/ctoken` | C-Series placeholder (never written to — C-Series has no OAuth token). |

`{store_id}` = the integer `stores.id` primary key from the database. One path per DB row — no sharing.

**Critical**: `token_path` and `credentials_path` must never overlap. pyLightspeed will raise `ValueError` if they do. Always use `/token` and `/creds` suffixes.

### Standard credential key names

| Key | Used for |
|---|---|
| `LSR_CLIENT_ID` | R-Series OAuth client ID |
| `LSR_CLIENT_SECRET` | R-Series OAuth client secret |
| `LSR_ACCOUNT_ID` | R-Series account / store ID |
| `LSC_API_KEY` | C-Series API key |
| `LSC_API_SECRET` | C-Series API secret |
| `LSC_API_HOST` | C-Series host override (optional) |
| `LSC_API_PATH` | C-Series path template override (optional) |
| `LSX_DOMAIN_PREFIX` | X-Series domain prefix |
| `LSX_PERSONAL_TOKEN` | X-Series personal access token |
| `LSX_CLIENT_ID` | X-Series OAuth client ID |
| `LSX_CLIENT_SECRET` | X-Series OAuth client secret |

---

## Step 1 — Install pyLightspeed with Vault support

```toml
# pyproject.toml
dependencies = [
    "pylightspeed[vault,mysql]",
]

[tool.uv.sources]
pylightspeed = { path = "../pyLightspeed", editable = true }
```

```powershell
uv sync
```

---

## Step 2 — Populate Vault

**Important — path convention for Lightspeed vs BottleManager services:**

`hvac_helper.read()` and `write()` follow the `bottlemanager/{env}/{service}` convention.
Lightspeed credentials live under a **separate** `lightspeed/` root that has its own
per-store structure — they do **not** go through the `bottlemanager` namespace.

For Lightspeed paths, use:
- `vault.read_paths([...])` to read (explicit paths, no namespace processing)
- `vault.client()` (raw `hvac`) to write during setup — `pyLightspeed` writes token
  paths automatically on every OAuth refresh

```python
import hvac_helper as vault

c = vault.client()   # authenticated hvac.Client
MOUNT = "secret"

# Shared OAuth app credentials (once — applies to all stores)
c.secrets.kv.v2.create_or_update_secret(
    path="lightspeed/shared",
    secret={
        "LSR_CLIENT_ID": "your-client-id",
        "LSR_CLIENT_SECRET": "your-client-secret",
        # Optional C-Series defaults:
        # "LSC_API_HOST": "api.shoplightspeed.com",
        # "LSC_API_PATH": "/us/{}",
    },
    mount_point=MOUNT,
)

# Per-store static credentials (repeat for each stores.id row)
store_id = 1
c.secrets.kv.v2.create_or_update_secret(
    path=f"lightspeed/stores/{store_id}/creds",
    secret={
        "LSR_ACCOUNT_ID": "123456",
        "LSC_API_KEY": "your-ecom-key",
        "LSC_API_SECRET": "your-ecom-secret",
    },
    mount_point=MOUNT,
)
# NOTE: Do NOT pre-write the /token path — pyLightspeed creates it on first OAuth exchange.
```

To read Lightspeed credentials from a script (outside of pyLightspeed's token store):
```python
creds = vault.read_paths([
    "lightspeed/shared",
    f"lightspeed/stores/{store_id}/creds",
])
print(creds["LSR_CLIENT_ID"])
```

> Alternatively use the Vault UI or CLI: `vault kv put secret/lightspeed/shared LSR_CLIENT_ID=...`

---

## Step 3 — The recommended store pattern (Vault primary + MySQL fallback)

All BottleManager apps use `CompositeTokenStore` so that:
1. Vault is authoritative for credentials
2. The MySQL `stores.config` column always holds a current token as a live fallback
3. If Vault is temporarily unavailable, the app keeps running with the MySQL-stored token

```python
from pylightspeed import (
    LightspeedRSeriesApi,
    VaultTokenStore,
    StoresTableTokenStore,
    CompositeTokenStore,
)

def get_rseries_api(store_id: int) -> LightspeedRSeriesApi:
    vault_store = VaultTokenStore(
        token_path=f"lightspeed/stores/{store_id}/token",
        credentials_path=[
            "lightspeed/shared",                          # LSR_CLIENT_ID, LSR_CLIENT_SECRET
            f"lightspeed/stores/{store_id}/creds",        # LSR_ACCOUNT_ID
        ],
    )
    mysql_store = StoresTableTokenStore(
        store_id=store_id,
        config_key="LSRETAIL_TOKEN",           # where the token lives in stores.config JSON
        credentials_config_key="LSRETAIL_CREDS",  # fallback creds in stores.config JSON (optional)
    )
    token_store = CompositeTokenStore(
        credentials=[mysql_store, vault_store],    # merged L→R; Vault wins on conflict
        token_read=vault_store,                    # read from Vault
        token_write=[vault_store, mysql_store],    # write to both — keeps MySQL current
    )
    return LightspeedRSeriesApi(token_store=token_store)
```

### C-Series (eCom)

C-Series uses static API keys — no OAuth token rotation. Use a placeholder `ctoken` path
so `VaultTokenStore` never writes to the credentials path.

```python
from pylightspeed import LightspeedCSeriesApi, VaultTokenStore, StoresTableTokenStore, CompositeTokenStore

def get_cseries_api(store_id: int) -> LightspeedCSeriesApi:
    vault_store = VaultTokenStore(
        token_path=f"lightspeed/stores/{store_id}/ctoken",   # never written; C-Series has no OAuth
        credentials_path=[
            "lightspeed/shared",                             # LSC_API_HOST, LSC_API_PATH
            f"lightspeed/stores/{store_id}/creds",           # LSC_API_KEY, LSC_API_SECRET
        ],
    )
    mysql_store = StoresTableTokenStore(
        store_id=store_id,
        credentials_config_key="LSECOM_CREDS",   # optional MySQL fallback
    )
    token_store = CompositeTokenStore(
        credentials=[mysql_store, vault_store],
        token_read=vault_store,
        token_write=[vault_store],    # C-Series: no token writes needed
    )
    return LightspeedCSeriesApi(token_store=token_store)
```

### X-Series (personal token — Plus plan)

```python
from pylightspeed import LightspeedXSeriesApi, VaultTokenStore

def get_xseries_api(store_id: int) -> LightspeedXSeriesApi:
    vault_store = VaultTokenStore(
        token_path=f"lightspeed/stores/{store_id}/xtoken",
        credentials_path=[
            "lightspeed/shared",
            f"lightspeed/stores/{store_id}/creds",   # LSX_DOMAIN_PREFIX, LSX_PERSONAL_TOKEN
        ],
    )
    return LightspeedXSeriesApi(token_store=vault_store)
```

---

## Step 4 — First-time OAuth flow (R-Series only)

R-Series requires completing an OAuth exchange before the token exists in Vault.
Use the built-in interactive CLI script — do not write a one-off script for this:

```powershell
# From the pyLightspeed repo root:
uv run scripts/reauthorize_rseries.py
```

The script will:
1. Detect which token store is configured (file, MySQL, or Vault) from env vars, or prompt you to choose
2. Load `LSR_CLIENT_ID` / `LSR_CLIENT_SECRET` from the store's `load_credentials()` or from `.env` / env vars
3. Open the Lightspeed authorization URL in your browser
4. Wait for you to paste back the redirect URL
5. Exchange the code and save the token to the chosen store

For Vault storage, set these before running:

```env
VAULT_ADDR=http://vault.local:8200/
VAULT_TOKEN=your-token
VAULT_LSR_TOKEN_PATH=lightspeed/stores/1/token
VAULT_LSR_CREDENTIALS_PATHS=lightspeed/shared,lightspeed/stores/1/creds
```

On success, the token is written to `lightspeed/stores/{id}/token` in Vault.
If you also used a `CompositeTokenStore` with MySQL, the MySQL fallback is kept current
automatically on every subsequent token refresh by pyLightspeed — no manual step needed.

---

## Step 5 — Verify the connection

```python
api = get_rseries_api(store_id=1)
account = api.account.fetch(api.connection.account_id)
print(account["name"])   # should print your store name
```

---

## Decision Guide

| Situation | What to use |
|---|---|
| New addition to bottleadmin / bottlemover | `CompositeTokenStore` (Vault+MySQL, §2.6 pattern above) |
| Quick script / one-off job | `VaultTokenStore` alone — no MySQL needed |
| Development / local test (no Vault) | `FileTokenStore(path="tokens/dev.json", credentials_file="creds/dev.json")` |
| Vault unavailable, want MySQL-only fallback | Replace `get_rseries_api()` call with `LightspeedRSeriesApi(token_store=mysql_store)` |
| Checking what credentials a store will resolve | `vault_store.load_credentials()` — returns the merged dict before any API call |

---

## Debugging

**`MissingCredentialsError`** — `LSR_CLIENT_ID` or `LSR_CLIENT_SECRET` not found:
```python
from pylightspeed import VaultTokenStore
vs = VaultTokenStore(token_path="lightspeed/stores/1/token",
                     credentials_path=["lightspeed/shared", "lightspeed/stores/1/creds"])
print(vs.load_credentials())   # inspect what Vault actually returned
```

**`MissingTokenError`** — no token at the Vault path yet. Run the OAuth flow (Step 4).

**`ValueError: token_path must not be the same as credentials_path`** — you used the same Vault path for both. Add `/token` and `/creds` suffixes.

**`RuntimeError: Vault client is not authenticated`** — `VAULT_ADDR` or `VAULT_TOKEN` env var is missing or wrong. Confirm `.env.local` is loaded in your launch config.

**Token not refreshing / stale** — `VaultTokenStore` uses `VaultCASLock` for distributed locking. If a `.lock` file is stuck, delete it manually (file-based lock) or check `lightspeed/stores/{id}/token_lock` in Vault.
