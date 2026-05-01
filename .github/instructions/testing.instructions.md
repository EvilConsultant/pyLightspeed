---
applyTo: "tests/**"
---

# Running Tests — pyLightspeed

## Project layout

This project uses a `src/` layout managed by `uv`. `pylightspeed` is installed
as an editable package only inside the project's `.venv`, **not** on the system
Python path. Always use the venv Python when running pytest.

## Correct command (Windows)

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q
```

For all tests (excluding integration):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q -m "not integration"
```

For integration tests (requires a valid `.env` with live credentials):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q -m integration
```

## Why not `python -m pytest` or `uv run pytest`?

- `python -m pytest` — uses the system/Anaconda Python, which does not have
  `pylightspeed` on its path → `ModuleNotFoundError`.
- `uv run pytest` — fails with "Failed to canonicalize script path" on Windows
  in this environment.

## Test markers

- `@pytest.mark.integration` — requires live Lightspeed API credentials in `.env`.
  Not run by default in CI. Skip with `-m "not integration"`.

## Test files

| File | Purpose |
|---|---|
| `tests/test_api.py` | Unit tests — no network, no credentials needed |
| `tests/test_integration.py` | Live API smoke tests — needs `.env` |
| `tests/test_live_resources.py` | Additional live resource tests |
