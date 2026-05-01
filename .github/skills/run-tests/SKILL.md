---
name: run-tests
description: 'Run tests, execute pytest, verify changes, run test suite, unit tests, integration tests in this project. Use when running any tests for pyLightspeed.'
---

# Running Tests in pyLightspeed

## When to Use
- Running pytest or the test suite
- Verifying a change didn't break anything
- Running unit tests or integration tests
- Checking test results

## Critical: Only One Command Works

This project uses a `src/` layout with a `uv`-managed virtual environment. Two common approaches **fail**:

| Command | Result |
|---------|--------|
| `python -m pytest` | `ModuleNotFoundError: No module named 'pylightspeed'` — system Python doesn't have the package |
| `uv run pytest` | "Failed to canonicalize script path" error on Windows |

**Always use:**
```
.\.venv\Scripts\python.exe -m pytest
```

## Procedure

### Step 1: Determine scope

Ask (or infer from context):
- **Unit tests only** (default, no external calls) → proceed to Step 2a
- **Integration tests** (require live Lightspeed credentials) → proceed to Step 2b
- **All tests** → proceed to Step 2c

### Step 2a: Run unit tests (default)

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q -m "not integration"
```

Or target a specific file:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q
```

### Step 2b: Run integration tests only

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q -m integration
```

Integration tests require live Lightspeed API credentials configured in the environment.

### Step 2c: Run all tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

## Interpreting Results

- **All green**: Changes are safe.
- **Failures**: Read the traceback. Common causes:
  - Import errors → check `src/pylightspeed/__init__.py` exports
  - `AttributeError` on a renamed method → verify 2.0 renames (`fetch`, `flat_dict`, `list_all`, `iter_all`)
  - Integration test failures → check credentials / live API availability

## Test Markers

Tests marked `@pytest.mark.integration` require live API access and are excluded from the default run. Unit tests have no marker.
