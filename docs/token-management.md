# Token Management

pyLightspeed uses OAuth 2.0 for R-Series and X-Series connections. Managing those tokens correctly
is critical: Lightspeed issues **single-use refresh tokens** — once a refresh token is exchanged
for a new access token, the old refresh token is permanently revoked. If two processes race to
exchange the same refresh token simultaneously, one of them ends up with a revoked token and all
subsequent API calls will fail with `401 Unauthorized`.

This guide covers how pyLightspeed stores tokens, how it prevents race conditions, and how to choose
the right strategy for your deployment.

---

## Token Storage — `TokenStore`

Every OAuth connection requires a `TokenStore`: an object that knows how to **load** and **save**
the token dict. pyLightspeed ships four built-in implementations and an abstract base class for
custom stores.

### Token dict format

All stores work with the same dict:

```python
{
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "Bearer",
    "scope": "employee:all ...",
    "expires_in": 1800,       # seconds (Lightspeed issues 30-minute tokens)
    "last_run": 1741785600.0  # Unix timestamp at last refresh — set by pyLightspeed
}
```

`last_run + expires_in` gives the absolute expiry time. pyLightspeed treats a token as expired
60 seconds *before* that wall-clock time (`expiry_buffer=60`) to provide a safety margin.

---

### `FileTokenStore`

Stores the token as a JSON file using atomic writes (`os.replace`) to prevent corruption if the
process is interrupted mid-write.

```python
from pylightspeed.connection import FileTokenStore
from pylightspeed import LightspeedRSeriesApi

store = FileTokenStore(
    path="/var/run/lightspeed/token.json",
    credentials_file="/etc/lightspeed/creds.json",  # optional
)
api = LightspeedRSeriesApi(token_store=store)
```

Use `credentials_file` to keep static credentials (client ID, client secret, account ID) in a
separate read-only file that `FileTokenStore` never modifies.

**Locking behaviour:** `FileTokenStore` uses `FileLock` automatically. All processes on the
**same machine** that share the same `path` will serialise their refresh attempts — only one calls
Lightspeed's OAuth endpoint; the rest wait and reuse its result.

---

### `VaultTokenStore`

Stores the token in **HashiCorp Vault** (KV v2). This is the recommended store for production
multi-app deployments.

```python
from pylightspeed.connection import VaultTokenStore
from pylightspeed import LightspeedRSeriesApi

store = VaultTokenStore(
    token_path="lightspeed/stores/1/token",
    credentials_path=[
        "lightspeed/shared",          # LSR_CLIENT_ID, LSR_CLIENT_SECRET
        "lightspeed/stores/1/creds",  # LSR_ACCOUNT_ID
    ],
    # vault_addr and vault_token default to VAULT_ADDR / VAULT_TOKEN env vars
)
api = LightspeedRSeriesApi(token_store=store)
```

`credentials_path` may be a single path or a list merged left-to-right, so shared secrets can live
in one path and store-specific values in another.

!!! warning "Separate token and credentials paths"
    `token_path` and any entry in `credentials_path` **must not overlap**. Writing a token to the
    same path as your credentials would silently overwrite them (KV v2 replaces the entire secret
    on each write). Use distinct paths such as
    `lightspeed/stores/1/token` and `lightspeed/stores/1/creds`.

**Locking behaviour:** `VaultTokenStore` automatically installs a [`VaultCASLock`](#vaultcaslock)
at construction time, keyed to `token_path + "_lock"`. This provides **fully distributed mutual
exclusion** — any number of processes on any number of machines will serialise correctly. See
[Distributed Locking](#distributed-locking-vaultcaslock) below.

Requires `hvac`: `uv add 'pylightspeed[vault]'`

---

### `MySQLTokenStore` / `StoresTableTokenStore`

Stores the token as a JSON column in a MySQL database. Useful when Vault is not available but you
still need a centralised token store shared across multiple processes.

```python
from pylightspeed.connection import StoresTableTokenStore

store = StoresTableTokenStore(
    store_id=1,
    config_key="lightspeed_token",         # JSON key inside the config column
    credentials_config_key="lightspeed_creds",  # optional
    host="db.internal",
    user="lightspeed",
    password="...",
    database="bottlemanager",
)
```

**Locking behaviour:** Uses `FileLock` (single-machine). Cross-machine locking for MySQL-backed
stores is not built in — if you run multiple servers sharing a MySQL token store, wrap the store in
a `CompositeTokenStore` or handle coordination externally.

---

### `EnvTokenStore`

Read-only store backed by environment variables or an explicit dict. Returns credentials but
can never save a token — use it as the credentials component of a `CompositeTokenStore`.

```python
from pylightspeed.connection import EnvTokenStore

# Reads LSR_CLIENT_ID, LSR_CLIENT_SECRET, LSR_ACCOUNT_ID, etc. from os.environ
creds = EnvTokenStore()
```

---

### `CompositeTokenStore`

Assembles credentials and token I/O from multiple independent stores. The most common pattern is
environment/Vault credentials combined with a writable token store.

```python
from pylightspeed.connection import CompositeTokenStore, EnvTokenStore, FileTokenStore

vault_store = ...  # your VaultTokenStore

store = CompositeTokenStore(
    credentials=[EnvTokenStore(), vault_store],  # merged left-to-right
    token_read=vault_store,
    token_write=[vault_store, FileTokenStore("/tmp/backup_token.json")],
)
```

---

## The Refresh Race — Why It Matters

Lightspeed's refresh tokens are **single-use**: the moment a new access token is used, the
refresh token that produced it is invalidated. If two processes simultaneously exchange the same
refresh token, only one exchange is accepted — the other process receives a valid-looking response
but its access token will silently fail on first use (or cause the other process's new refresh
token to be revoked, depending on Lightspeed's revocation order).

This is a real problem when:

- A Dagster multiprocess executor spawns multiple workers that each create their own API connection
- Multiple applications (e.g. bottleadmin, bottlemover, a background job) all use pyLightspeed
  and the token expires while all are active simultaneously

---

## Token Locking — `TokenLock`

Every `TokenStore` has a `_lock` property that returns a `TokenLock` — an object responsible for
ensuring that `atomic_refresh` is only executed by one caller at a time, regardless of threads or
processes.

```
TokenLock (ABC)
├── FileLock        — cross-process, single machine  (default for all stores)
├── NullLock        — no-op (tests, externally serialised workflows)
└── VaultCASLock    — distributed, any number of machines  (default for VaultTokenStore)
```

You can replace the default lock on any store:

```python
from pylightspeed.connection import FileTokenStore, NullLock

# In a Hatchet workflow with concurrencyLimit=1, locking is handled externally
store = FileTokenStore("/path/to/token.json")
store._lock = NullLock()
```

---

### `FileLock`

The default for all stores except `VaultTokenStore`. Creates a lock file in the system temp
directory (`$TMPDIR` / `%TEMP%`) using `os.O_CREAT | os.O_EXCL` which is atomic on both Linux
and Windows. Also acquires a per-path `threading.Lock` so threads within the same process
queue up without redundant filesystem round-trips.

- **Scope:** all processes on the same machine
- **Stale lock handling:** files older than 60 seconds (holder crashed) are removed automatically
- **Timeout:** raises `TimeoutError` after 30 seconds

The lock file name is derived from a SHA-1 hash of the `_lock_key()` so that all instances
pointing at the same token path share the same lock file.

---

### Distributed Locking — `VaultCASLock`

`VaultCASLock` provides a **fully distributed mutex** backed by a dedicated Vault KV v2 key.
It is installed automatically by `VaultTokenStore` at construction time — you do not need to
configure it manually.

**How it works:**

1. A dedicated lock path (e.g. `lightspeed/stores/1/token_lock`) is used exclusively as a mutex.
   It never holds any meaningful data — its *existence* is the lock.
2. To acquire: read the lock key and its current version. If the `holder` field is absent or
   `null` (or the entry is stale — older than 60 s, indicating a crash), attempt a CAS write
   with the observed version. Vault processes CAS writes atomically server-side: exactly one
   winner per version.
3. All losers (CAS conflict) spin at 100 ms intervals and retry.
4. The one winner reads the actual token, checks if it is still stale (re-check under lock),
   and only calls Lightspeed's OAuth endpoint if needed.
5. On release: write `{"holder": null}` (no CAS needed — only the winner calls release).

**Result with 20 concurrent callers:**

| Step | What happens |
|------|--------------|
| All 20 attempt CAS-acquire | Vault grants exactly 1; 19 spin |
| Winner reads token | Checks expiry under lock |
| Winner calls Lightspeed | 1 OAuth call total |
| Winner writes new token | Normal Vault write |
| Winner releases lock | Writes `{"holder": null}` |
| Each of the 19 acquires in turn | Re-reads token, sees it's fresh, returns immediately |
| **Total OAuth calls** | **1** |

!!! note "Thread safety within a process"
    `VaultCASLock` also acquires a per-path `threading.Lock` before any Vault operation, so
    threads within the same process serialise without redundant Vault round-trips.

---

## `atomic_refresh` — The Unified Entry Point

All refresh coordination flows through `TokenStore.atomic_refresh()`, implemented on the base class:

```
acquire lock (via self._lock)
  └── re-read token from store
      ├── token is fresh? → return (codes, was_refreshed=False)
      └── token is stale?
            └── call do_refresh_fn(codes) → new_token_data
                └── save_token(new_token_data)
                    └── release lock
                        └── return (new_token_data, was_refreshed=True)
```

Every caller that waited for the lock re-reads the token on entry. Any process that arrives after
the winner has already written the new token will find it fresh and skip the OAuth call entirely.

---

## Choosing the Right Store

| Deployment | Recommended store | Locking |
|------------|-------------------|---------|
| Single script / notebook | `FileTokenStore` | `FileLock` (automatic) |
| Single server, multiple processes | `FileTokenStore` | `FileLock` (automatic) |
| Single server, centralised token | `VaultTokenStore` | `VaultCASLock` (automatic) |
| Multiple servers (e.g. bottleadmin + bottlemover) | `VaultTokenStore` | `VaultCASLock` (automatic) |
| External orchestrator handles concurrency | Any store | `NullLock` |

---

## Dagster Integration

When Dagster's multiprocess executor spawns workers they each initialise API connections nearly
simultaneously, making token refresh races very likely. The recommended pattern is to:

1. Use `VaultTokenStore` (distributed lock prevents all cross-process and cross-machine races)
2. Use `setup_for_execution` in the Dagster resource to pre-warm the token in each worker
   *before* the asset body runs

```python
from dagster import ConfigurableResource
from pydantic import Field, PrivateAttr
from typing import Any

class LightspeedRSeriesResource(ConfigurableResource):
    store_id: int = Field(default=1)
    _api: Any = PrivateAttr(default=None)

    def _vault_store(self):
        from pylightspeed import VaultTokenStore
        return VaultTokenStore(
            token_path=f"lightspeed/stores/{self.store_id}/token",
            credentials_path=[
                "lightspeed/shared",
                f"lightspeed/stores/{self.store_id}/creds",
            ],
        )

    def setup_for_execution(self, context) -> None:
        """Pre-warm the OAuth token before any op executes.

        Called by Dagster in each worker. VaultCASLock ensures only one
        worker calls Lightspeed's OAuth endpoint; all others wait and
        reuse the result.
        """
        from pylightspeed import LightspeedRSeriesApi
        self._api = LightspeedRSeriesApi(token_store=self._vault_store())

    def get_api(self):
        if self._api is None:
            from pylightspeed import LightspeedRSeriesApi
            self._api = LightspeedRSeriesApi(token_store=self._vault_store())
        return self._api
```

`setup_for_execution` runs in each worker process before the asset body. The `VaultCASLock` on
`VaultTokenStore` ensures that however many workers call `atomic_refresh` simultaneously, only one
calls Lightspeed — the rest wait (typically < 1 second) and pick up the fresh token.

---

## API Reference

::: pylightspeed.connection.TokenStore
    options:
      members:
        - load_token
        - save_token
        - load_credentials
        - atomic_refresh
        - _lock
        - _lock_key

::: pylightspeed.connection.TokenLock
    options:
      members:
        - acquire

::: pylightspeed.connection.FileLock

::: pylightspeed.connection.NullLock

::: pylightspeed.connection.VaultCASLock

::: pylightspeed.connection.FileTokenStore

::: pylightspeed.connection.VaultTokenStore

::: pylightspeed.connection.EnvTokenStore

::: pylightspeed.connection.CompositeTokenStore
