---
name: migrate-to-v2
description: 'Migrate an application to pyLightspeed 2.0. Use when updating bottlemover, bottleadmin, or any app that imports pyLightspeed to fix breaking changes, update method names, or switch to the new token store system.'
---

# Migrating an Application to pyLightspeed 2.0

## When to Use
- Updating an application (bottlemover, bottleadmin, etc.) that depends on pyLightspeed
- Fixing `AttributeError` or `ImportError` after upgrading to pyLightspeed 2.0
- Implementing the token store system for credential and OAuth token management
- Replacing old credential-passing patterns with the new store-based approach

---

## Part 1 — Breaking Changes (Required for all apps)

### 1.0 `LightspeedStore` removed

`LightspeedStore` (from `pylightspeed.store`) has been removed. Any code that instantiates it will raise `RuntimeError` immediately.

Replace with the token store pattern described in Part 2. The recommended replacement for apps that already use a `stores` MySQL table is documented in §2.6 (Vault-primary with MySQL fallback).

### 1.1 Exception import path

`exception.py` was renamed to `exceptions.py`.

```python
# Before
from pylightspeed.exception import HttpException

# After
from pylightspeed.exceptions import HttpException
# or just catch via the top-level package
from pylightspeed import MissingCredentialsError
```

### 1.2 HTTP fetch method renamed: `.get()` → `.fetch()`

`ApiResource.get(id)` and `ApiSubResource.get(parentid, id)` are now `.fetch()`.

This was a critical collision: `ApiResource` inherits from `dict`, so calling `resource.get(key)` invoked the HTTP classmethod instead of `dict.get`. The rename resolves this permanently.

```python
# Before
item = api.items.get(item_id)
contact = Contacts.get(customer_id, contact_id, connection=api.connection)

# After
item = api.items.fetch(item_id)
contact = Contacts.fetch(customer_id, contact_id, connection=api.connection)
```

Sub-resources also renamed — check your own code for any `.get(` calls on pyLightspeed resource classes.

**If you needed dict-style access before (now safe):**
```python
# This now safely calls dict.get, not the HTTP method
value = resource.get("someField", default)
```

### 1.3 `Mapping` → `AttrDict`

The base dot-access dict class was renamed.

```python
# Before
from pylightspeed.resources.base import Mapping

# After
from pylightspeed.resources.base import AttrDict
# or via top-level (re-exported)
from pylightspeed import AttrDict
```

### 1.4 `nested_json_to_attr()` → `_map_fields()`

The method that derives convenience attributes from nested API data is now private and called `_map_fields()`. It is called automatically by `flat_dict()` and by resource `__init__` where needed.

```python
# Before (direct call)
item.nested_json_to_attr()
price = item.price_default

# After — just access the attr directly or call flat_dict()
flat = item.flat_dict()   # triggers _map_fields() internally
price = item.price_default  # available after flat_dict() or fetch()
```

You should not need to call `_map_fields()` directly. If you did call `nested_json_to_attr()` explicitly before saving a record to a database, replace it with `flat_dict()`.

### 1.5 `as_dict()` → `flat_dict()`

```python
# Before
row = item.as_dict()

# After
row = item.flat_dict()
```

`flat_dict()` returns only scalar values (`str`, `int`, `float`, `bool`, `None`). Nested dicts and lists are excluded. Use `dict(resource)` if you need the full nested structure.

### 1.6 `listall()` / `iterall()` → `list_all()` / `iter_all()`

```python
# Before
all_items = api.items.listall(connection=api.connection)
for item in api.items.iterall(connection=api.connection):
    ...

# After
all_items = api.items.list_all(connection=api.connection)
for item in api.items.iter_all(connection=api.connection):
    ...
```

### 1.7 `ListableRetailApiResource` removed

This class no longer exists. Resource classes use `ListableApiResource` or the series-specific base (`RSeriesApiResource`, `XSeriesApiResource`, `ESeriesApiResource`) directly.

```python
# Before
class MyResource(ListableRetailApiResource):
    ...

# After
from pylightspeed.resources.rseries.rseriesbase import RSeriesApiResource

class MyResource(RSeriesApiResource):
    ...
```

---

## Part 2 — Token Store System (replaces manual credential files)

pyLightspeed 2.0 introduces a unified `TokenStore` abstraction. All `LightspeedXxxApi` constructors accept a `token_store` parameter. The store handles both the rotating OAuth token and the static connection credentials (client ID, secret, account ID, etc.).

**Standard credential key names** used by all stores:

| Key | Used for |
|-----|----------|
| `LSR_CLIENT_ID` | R-Series OAuth client ID |
| `LSR_CLIENT_SECRET` | R-Series OAuth client secret |
| `LSR_ACCOUNT_ID` | R-Series account/store ID |
| `LSR_REDIRECT_URI` | R-Series OAuth redirect URI |
| `LSC_API_KEY` | C-Series API key |
| `LSC_API_SECRET` | C-Series API secret |
| `LSC_API_HOST` | C-Series host (optional override) |
| `LSC_API_PATH` | C-Series path template (optional override) |
| `LSX_DOMAIN_PREFIX` | X-Series domain prefix |
| `LSX_PERSONAL_TOKEN` | X-Series personal access token |
| `LSX_CLIENT_ID` | X-Series OAuth client ID |
| `LSX_CLIENT_SECRET` | X-Series OAuth client secret |

### 2.1 FileTokenStore — simple file-based storage

```python
from pylightspeed import FileTokenStore, LightspeedRSeriesApi

store = FileTokenStore(
    path="tokens/my_store.json",          # rotating OAuth token
    credentials_file="creds/my_store.json"  # static credentials (optional)
)
api = LightspeedRSeriesApi(token_store=store)
```

`credentials_file` should be a JSON file with the standard key names. The `token_file` path is written automatically on each token refresh.

### 2.2 VaultTokenStore — HashiCorp Vault (KV v2)

Requires `hvac`: `uv add 'pylightspeed[vault]'`

**Path convention** for all tools in this project:

| Vault path | Contents |
|------------|----------|
| `lightspeed/stores/{store_id}/token` | Rotating OAuth token (written on every refresh) |
| `lightspeed/stores/{store_id}/creds` | Static credentials (`LSR_CLIENT_ID`, etc.) |
| `lightspeed/shared` | Credentials shared across all stores (client ID/secret) |

Always use `store_id` (the integer primary key from the `stores` table) as the path component so there is a 1-to-1 mapping between Vault paths and database rows.

```python
from pylightspeed import VaultTokenStore, LightspeedRSeriesApi

store_id = 42  # stores.id from the database

vault = VaultTokenStore(
    token_path=f"lightspeed/stores/{store_id}/token",
    credentials_path=[
        "lightspeed/shared",                       # shared client_id / client_secret
        f"lightspeed/stores/{store_id}/creds",     # store-specific account_id, etc.
    ],
    # vault_addr and vault_token default to VAULT_ADDR / VAULT_TOKEN env vars
)
api = LightspeedRSeriesApi(token_store=vault)
```

**Critical rule**: `token_path` must never be the same as any `credentials_path` entry. The token write overwrites the entire KV v2 secret at that path and would destroy your credentials.

```python
# WRONG — will raise ValueError
VaultTokenStore(
    token_path="lightspeed/stores/42",
    credentials_path="lightspeed/stores/42",  # same path!
)

# CORRECT — separate paths (always use /token and /creds suffixes)
VaultTokenStore(
    token_path="lightspeed/stores/42/token",
    credentials_path="lightspeed/stores/42/creds",
)
```

Vault credentials are cached after the first read — Vault is not re-queried within the same process lifetime.

### 2.3 EnvTokenStore — environment variables (read-only credentials)

Useful when credentials are already loaded into the environment (e.g. via `python-dotenv`). Cannot store tokens — pair with a writable store via `CompositeTokenStore`.

```python
from pylightspeed import EnvTokenStore
# Reads LSR_CLIENT_ID, LSR_CLIENT_SECRET, LSR_ACCOUNT_ID, etc. from os.environ
```

### 2.4 CompositeTokenStore — mix and match backends

Use when credentials and tokens live in different backends, or when you want multiple token write targets.

Rules:
- Credentials are merged **left-to-right** — later stores override earlier ones.
- Token reads come from exactly one `token_read` store.
- Token writes go to **all** `token_write` stores (independently — no fallback logic).
- `token_read` store need not be in `token_write` — the lists are independent.

### 2.5 StoresTableTokenStore — built-in MySQL store for the `stores` table

`StoresTableTokenStore` reads and writes tokens inside a `config` JSON column on the `stores` table, keyed by `stores.id`. This is a concrete, ready-to-use implementation — no subclassing needed.

It also supports loading credentials from a separate JSON key on the same row via `credentials_config_key`.

```python
from pylightspeed import StoresTableTokenStore, LightspeedRSeriesApi

# DB connection defaults to MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB
mysql_store = StoresTableTokenStore(
    store_id=42,                              # stores.id primary key
    config_key="LSRETAIL_TOKEN",              # default — where the token is stored in stores.config
    credentials_config_key="LSRETAIL_CREDS", # optional — where credentials live in stores.config
)
api = LightspeedRSeriesApi(token_store=mysql_store)
```

Requires: `uv add 'pylightspeed[mysql]'`

### 2.6 Recommended pattern: Vault primary + MySQL fallback

Vault is the primary credential and token store. The MySQL `stores` table remains as a fallback in case Vault is ever unavailable, and the token is written to both on every refresh so the fallback stays current.

```python
from pylightspeed import (
    CompositeTokenStore, VaultTokenStore, StoresTableTokenStore,
    LightspeedRSeriesApi,
)

store_id = 42  # stores.id integer primary key

vault = VaultTokenStore(
    token_path=f"lightspeed/stores/{store_id}/token",
    credentials_path=[
        "lightspeed/shared",
        f"lightspeed/stores/{store_id}/creds",
    ],
)

mysql = StoresTableTokenStore(
    store_id=store_id,
    config_key="LSRETAIL_TOKEN",
    credentials_config_key="LSRETAIL_CREDS",  # keep credentials in stores.config as fallback
)

store = CompositeTokenStore(
    credentials=vault,        # Vault is the authoritative credentials source
    token_read=vault,         # read from Vault
    token_write=[vault, mysql],  # write to both — keeps MySQL current as fallback
)
api = LightspeedRSeriesApi(token_store=store)
```

**To switch to MySQL-only** (if Vault is unavailable):
```python
api = LightspeedRSeriesApi(token_store=mysql)
```

No other code changes are needed — the `stores` table still holds a valid, up-to-date token because every refresh wrote to it.

---

## Part 3 — Logging

pyLightspeed emits no logs by default. To enable debug logging in a consuming app:

```python
from loguru import logger
logger.enable("pylightspeed")
```

---

## Part 4 — Quick Migration Checklist

When updating an existing app:

- [ ] Remove all `LightspeedStore` usage — replace with `VaultTokenStore` + `StoresTableTokenStore` via `CompositeTokenStore` (see §2.6)
- [ ] Replace `from pylightspeed.exception import` → `from pylightspeed.exceptions import`
- [ ] Replace `.get(id)` with `.fetch(id)` on all resource classmethods
- [ ] Replace `.listall(` with `.list_all(`
- [ ] Replace `.iterall(` with `.iter_all(`
- [ ] Replace `.as_dict()` with `.flat_dict()`
- [ ] Replace `nested_json_to_attr()` calls with `flat_dict()` (or remove if only needed for field access)
- [ ] Replace `Mapping` import with `AttrDict`
- [ ] Replace `ListableRetailApiResource` base class with the series-specific base
- [ ] Replace direct credential passing with a `TokenStore` (FileTokenStore is the simplest swap)
- [ ] If using VaultTokenStore: verify `token_path` ≠ any `credentials_path` entry (use `/token` and `/creds` suffixes)
- [ ] Use `stores.id` as the Vault path component: `lightspeed/stores/{store_id}/token`
