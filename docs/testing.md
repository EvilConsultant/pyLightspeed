# Testing

pyLightspeed has three test suites that cover different layers of the library.
They all use **pytest** and are managed through **uv**.

---

## Overview

| Suite | File | Needs credentials | What it tests |
|---|---|---|---|
| Unit tests | `tests/test_api.py` | No | API class construction, connection config, token handling (mocked) |
| Basic integration | `tests/test_integration.py` | R-Series, C-Series | End-to-end smoke tests for a single resource per series |
| Full live resources | `tests/test_live_resources.py` | Per series | All CRUD methods across every resource, with JSON log output |

---

## Credentials

Live tests read credentials from environment variables.
Create a `.env` file in the repo root (it is gitignored):

```ini
# R-Series (Lightspeed Retail — OAuth)
LSR_ACCOUNT_ID=190211
LSR_CLIENT_ID=your_client_id
LSR_CLIENT_SECRET=your_client_secret
LSR_TOKEN_FILE=C:/path/to/your/.codes/store_codes.json

# C-Series (Lightspeed eCom — Basic Auth)
LSC_API_KEY=your_api_key
LSC_API_SECRET=your_api_secret
LSC_API_HOST=api.shoplightspeed.com   # optional
LSC_API_PATH=/us/{}                   # optional

# X-Series (Lightspeed Retail X — Personal Token)
LSX_DOMAIN_PREFIX=mystore
LSX_PERSONAL_TOKEN=your_personal_token

# E-Series (Ecwid)
LSE_STORE_ID=your_store_id
LSE_API_SECRET=your_api_secret
```

Any test whose credentials are absent is **automatically skipped** — the suite
stays green in CI with no credentials configured.

---

## Running the tests

All commands assume you are in the repo root.

### Unit tests only

No credentials required. Runs in under a second.

```bash
uv run pytest tests/test_api.py -v
```

### All tests (unit + integration)

```bash
uv run pytest tests/ -v
```

### Integration tests only

```bash
uv run pytest -m integration -v
```

### Skip integration tests explicitly

```bash
uv run pytest -m "not integration" -v
```

### A single series

```bash
uv run pytest -m integration tests/test_live_resources.py -k RSeries -v
uv run pytest -m integration tests/test_live_resources.py -k CSeries -v
uv run pytest -m integration tests/test_live_resources.py -k XSeries -v
uv run pytest -m integration tests/test_live_resources.py -k ESeries -v
```

---

## Unit tests (`test_api.py`)

Seventeen tests that require no network access.
All API objects are constructed with mocked credentials and the OAuth token
refresh is patched so no real HTTP calls are made.

Tests cover:

- `LightspeedCSeriesApi` — namespace, timestamp fields, host defaults, basic-auth tuple construction
- `LightspeedRSeriesApi` — namespace, timestamp fields, connection credentials, Bearer token injection, token refresh via `FileTokenStore`
- `LightspeedXSeriesApi` — namespace, timestamp fields, host construction from `domain_prefix`, Bearer token injection, error on missing credentials

---

## Basic integration tests (`test_integration.py`)

Six smoke tests that call the live API.
One resource is tested per series (Employees for R-Series, Filters for
C-Series).

Each resource is verified for:

- `page()` returns a non-empty list
- Expected fields are present on the first record
- `listall()` returns at least as many records as a single `page()`

---

## Full live resource tests (`test_live_resources.py`)

A parametrized suite that runs the full method set against every resource.
By default only one resource per series is included (the *smoke* resource).
Set `LIVE_ALL_RESOURCES=1` to sweep every resource in the manifests.

### Methods tested

| Method | What is checked |
|---|---|
| `page()` | Returns a non-empty list |
| `get(id)` | Returns the single record; correct id field present |
| `listall()` | Returns ≥ records than `page()` |
| `iterall(limit=25)` | Generator yields at least one item |
| `iter(limit=25)` | *(R-Series only)* offset/limit generator yields items |
| `count()` | *(C-Series only)* Returns a non-negative integer |

### Run with full resource sweep

```bash
$env:LIVE_ALL_RESOURCES=1
uv run pytest -m integration tests/test_live_resources.py -v
```

Or as a one-liner:

```bash
uv run pytest -m integration tests/test_live_resources.py -v --override-ini="env=LIVE_ALL_RESOURCES=1"
```

### Resource manifests

The resources included in each series are defined at the top of
`tests/test_live_resources.py` in the `*_RESOURCES` lists.
Add or remove resources there, and set `smoke: True` to include
a resource in the default run.

---

## Log output

Every live API call in `test_live_resources.py` is logged to a
**JSONL file** (one JSON object per line) under `tests/output/`:

```
tests/output/live_results_20260227_143022.log
```

The `tests/output/` directory is gitignored.

Each log entry looks like:

```json
{
  "ts": "2026-02-27T14:30:22.451",
  "series": "CSeries",
  "resource": "Filters",
  "method": "page()",
  "count": 12,
  "sample": [
    {"id": 9973, "title": "Grape Variety", "isActive": true},
    {"id": 9974, "title": "Red Grapes",    "isActive": true}
  ]
}
```

Up to three sample records are included per entry.
Nested objects and private keys (prefixed with `_`) are stripped
so the file remains clean and readable.

The log file is created at the start of each test session and closed
when the session ends, regardless of pass/fail status.
