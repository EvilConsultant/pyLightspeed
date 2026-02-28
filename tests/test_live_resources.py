"""
Comprehensive live-API integration tests for all four Lightspeed series.

Results (including raw JSON samples) are written to
``tests/output/live_results_<timestamp>.log`` in JSONL format — one JSON
object per line so the file is easy to parse or grep.

Usage
-----
Smoke run (one resource per series, default):
    pytest -m integration tests/test_live_resources.py -v

Full sweep of every resource:
    LIVE_ALL_RESOURCES=1 pytest -m integration tests/test_live_resources.py -v

Run only a specific series:
    pytest -m integration tests/test_live_resources.py -v -k RSeries

Required .env variables
-----------------------
R-Series:
    LSR_ACCOUNT_ID, LSR_CLIENT_ID, LSR_CLIENT_SECRET, LSR_TOKEN_FILE

C-Series:
    LSC_API_KEY, LSC_API_SECRET
    LSC_API_HOST  (optional, default api.shoplightspeed.com)
    LSC_API_PATH  (optional, default /us/{})

X-Series (Personal Token):
    LSX_DOMAIN_PREFIX   e.g. "mystore"
    LSX_PERSONAL_TOKEN

E-Series:
    LSE_STORE_ID
    LSE_API_SECRET
"""

import datetime
import json
import os
from pathlib import Path
from typing import Any

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from pylightspeed.api import (
    LightspeedCSeriesApi,
    LightspeedESeriesApi,
    LightspeedRSeriesApi,
    LightspeedXSeriesApi,
)

# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

#: Set LIVE_ALL_RESOURCES=1 to include every resource in the manifests below,
#: not just the one marked smoke=True per series.
ALL_RESOURCES: bool = os.environ.get("LIVE_ALL_RESOURCES", "").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# JSONL log — session-scoped, writes to tests/output/
# ---------------------------------------------------------------------------

_log_file = None  # module-level handle so helpers can write to it


@pytest.fixture(scope="session", autouse=True)
def _json_log_setup():
    """Open a JSONL log file for the session; close it when done."""
    global _log_file
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_dir / f"live_results_{ts}.log"
    _log_file = log_path.open("w", encoding="utf-8")
    _log_file.write(
        json.dumps({"ts": datetime.datetime.now().isoformat(), "event": "session_start"}) + "\n"
    )
    _log_file.flush()
    yield
    _log_file.write(
        json.dumps({"ts": datetime.datetime.now().isoformat(), "event": "session_end"}) + "\n"
    )
    _log_file.flush()
    _log_file.close()
    _log_file = None


def _to_jsonable(obj, _depth: int = 0):
    """Recursively convert API objects to plain JSON-safe types.

    Skips keys that start with ``_`` (e.g. ``_connection``) and recurses into
    nested dicts/lists up to a depth of 4 to avoid blowing up on huge trees.
    """
    if _depth > 4:
        return repr(obj)
    if isinstance(obj, dict):
        return {
            str(k): _to_jsonable(v, _depth + 1)
            for k, v in obj.items()
            if not str(k).startswith("_")
        }
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(i, _depth + 1) for i in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def _log(series: str, resource: str, method: str, result: Any) -> None:
    """Write a JSONL entry describing an API call result."""
    if _log_file is None:
        return
    try:
        if isinstance(result, list):
            count = len(result)
            sample = [_to_jsonable(item) for item in result[:3]]
        elif isinstance(result, dict):
            count = 1
            sample = [_to_jsonable(result)]
        else:
            count = result
            sample = repr(result)
    except Exception as exc:
        count = "error"
        sample = str(exc)

    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "series": series,
        "resource": resource,
        "method": method,
        "count": count,
        "sample": sample,
    }
    _log_file.write(json.dumps(entry) + "\n")
    _log_file.flush()


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _rseries_creds():
    keys = ("LSR_ACCOUNT_ID", "LSR_CLIENT_ID", "LSR_CLIENT_SECRET", "LSR_TOKEN_FILE")
    vals = [os.environ.get(k) for k in keys]
    if not all(vals):
        return None
    return dict(zip(("account_id", "client_id", "client_secret", "token_file"), vals))


def _cseries_creds():
    api_key = os.environ.get("LSC_API_KEY")
    api_secret = os.environ.get("LSC_API_SECRET")
    if not (api_key and api_secret):
        return None
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "host": os.environ.get("LSC_API_HOST", "api.shoplightspeed.com"),
        "api_path": os.environ.get("LSC_API_PATH", "/us/{}"),
    }


def _xseries_creds():
    domain_prefix = os.environ.get("LSX_DOMAIN_PREFIX")
    personal_token = os.environ.get("LSX_PERSONAL_TOKEN")
    if not (domain_prefix and personal_token):
        return None
    return {"domain_prefix": domain_prefix, "personal_token": personal_token}


def _eseries_creds():
    store_id = os.environ.get("LSE_STORE_ID")
    api_secret = os.environ.get("LSE_API_SECRET")
    if not (store_id and api_secret):
        return None
    return {"store_id": store_id, "api_secret": api_secret}


requires_rseries = pytest.mark.skipif(
    _rseries_creds() is None, reason="LSR_* credentials not set in env / .env"
)
requires_cseries = pytest.mark.skipif(
    _cseries_creds() is None, reason="LSC_* credentials not set in env / .env"
)
requires_xseries = pytest.mark.skipif(
    _xseries_creds() is None, reason="LSX_* credentials not set in env / .env"
)
requires_eseries = pytest.mark.skipif(
    _eseries_creds() is None, reason="LSE_* credentials not set in env / .env"
)

# ---------------------------------------------------------------------------
# Resource manifests
#
# Fields:
#   name       — attribute name on the API object (e.g. "Employees")
#   id_field   — primary-key field name in the returned dict
#   smoke      — True → included in default smoke run; False → ALL_RESOURCES only
#   has_count  — True → resource supports .count() (C-Series only currently)
# ---------------------------------------------------------------------------

RSERIES_RESOURCES = [
    {"name": "Employees",     "id_field": "employeeID",     "smoke": True,  "has_count": False},
    {"name": "Categories",    "id_field": "categoryID",     "smoke": False, "has_count": False},
    {"name": "Items",         "id_field": "itemID",         "smoke": False, "has_count": False},
    {"name": "Vendors",       "id_field": "vendorID",       "smoke": False, "has_count": False},
    {"name": "Manufacturers", "id_field": "manufacturerID", "smoke": False, "has_count": False},
    {"name": "Tags",          "id_field": "tagID",          "smoke": False, "has_count": False},
    {"name": "Customers",     "id_field": "customerID",     "smoke": False, "has_count": False},
]

CSERIES_RESOURCES = [
    {"name": "Filters",    "id_field": "id", "smoke": True,  "has_count": True},
    {"name": "Brands",     "id_field": "id", "smoke": False, "has_count": True},
    {"name": "Products",   "id_field": "id", "smoke": False, "has_count": True},
    {"name": "Variants",   "id_field": "id", "smoke": False, "has_count": True},
    {"name": "Customers",  "id_field": "id", "smoke": False, "has_count": True},
    {"name": "Orders",     "id_field": "id", "smoke": False, "has_count": True},
]

XSERIES_RESOURCES = [
    {"name": "Products",          "id_field": "id", "smoke": True,  "has_count": False},
    {"name": "ProductCategories", "id_field": "id", "smoke": False, "has_count": False},
    {"name": "ProductTypes",      "id_field": "id", "smoke": False, "has_count": False},
    {"name": "Brands",            "id_field": "id", "smoke": False, "has_count": False},
    {"name": "Outlets",           "id_field": "id", "smoke": False, "has_count": False},
    {"name": "Suppliers",         "id_field": "id", "smoke": False, "has_count": False},
    {"name": "Customers",         "id_field": "id", "smoke": False, "has_count": False},
    {"name": "Tags",              "id_field": "id", "smoke": False, "has_count": False},
]

ESERIES_RESOURCES = [
    {"name": "Products",          "id_field": "id", "smoke": True,  "has_count": False},
    {"name": "ProductCategories", "id_field": "id", "smoke": False, "has_count": False},
    {"name": "ProductTypes",      "id_field": "id", "smoke": False, "has_count": False},
    {"name": "Orders",            "id_field": "id", "smoke": False, "has_count": False},
]


def _active(manifest: list) -> list:
    """Return only the resources that should run under the current flag."""
    return manifest if ALL_RESOURCES else [r for r in manifest if r["smoke"]]


# ---------------------------------------------------------------------------
# Shared assertion helpers
# ---------------------------------------------------------------------------


def _assert_page(api_wrapper, resource: dict, series: str) -> list:
    """page() → non-empty list; logged."""
    result = api_wrapper.page()
    assert isinstance(result, list), (
        f"{series}.{resource['name']}.page() returned {type(result).__name__}, expected list"
    )
    assert len(result) > 0, f"{series}.{resource['name']}.page() returned an empty list"
    _log(series, resource["name"], "page()", result)
    return result


def _assert_get(api_wrapper, resource: dict, series: str, page_result: list):
    """get(id) → single object with expected id_field; logged."""
    first = page_result[0]
    item_id = first[resource["id_field"]]
    single = api_wrapper.get(item_id)
    assert single is not None, (
        f"{series}.{resource['name']}.get({item_id!r}) returned None"
    )
    assert resource["id_field"] in single, (
        f"Expected field '{resource['id_field']}' in .get() result; got: {list(single.keys())[:10]}"
    )
    _log(series, resource["name"], f"get({item_id!r})", [dict(single)])
    return single


def _assert_listall(api_wrapper, resource: dict, series: str, page_result: list) -> list:
    """listall() → list with len >= len(page()); logged."""
    all_items = api_wrapper.listall()
    assert isinstance(all_items, list), (
        f"{series}.{resource['name']}.listall() returned {type(all_items).__name__}"
    )
    assert len(all_items) >= len(page_result), (
        f"{series}.{resource['name']}.listall() returned {len(all_items)} items "
        f"but page() returned {len(page_result)}"
    )
    _log(series, resource["name"], "listall()", all_items)
    return all_items


def _assert_iterall(api_wrapper, resource: dict, series: str) -> list:
    """iterall(limit=25) with explicit limit → single-page branch; yields items; logged."""
    collected = list(api_wrapper.iterall(limit=25))
    assert len(collected) > 0, (
        f"{series}.{resource['name']}.iterall(limit=25) yielded no items"
    )
    _log(series, resource["name"], "iterall(limit=25)", collected)
    return collected


def _assert_count(api_wrapper, resource: dict, series: str):
    """count() → numeric value >= 0; logged. Only call when has_count=True."""
    raw = api_wrapper.count()
    assert raw is not None, f"{series}.{resource['name']}.count() returned None"
    numeric = int(raw)
    assert numeric >= 0, f"{series}.{resource['name']}.count() returned {raw!r}"
    _log(series, resource["name"], "count()", numeric)
    return numeric


# ---------------------------------------------------------------------------
# R-Series
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_rseries
class TestRSeriesResources:
    """Live end-to-end tests for Lightspeed Retail (R-Series) resources."""

    @pytest.fixture(scope="class")
    def api(self):
        return LightspeedRSeriesApi(**_rseries_creds())

    @pytest.mark.parametrize("resource", _active(RSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_page(self, api, resource):
        """page() returns a non-empty list."""
        _assert_page(getattr(api, resource["name"]), resource, "RSeries")

    @pytest.mark.parametrize("resource", _active(RSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_get(self, api, resource):
        """get(id) returns the individual record with the correct id field."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "RSeries")
        _assert_get(wrapper, resource, "RSeries", page_result)

    @pytest.mark.parametrize("resource", _active(RSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_listall(self, api, resource):
        """listall() returns at least as many records as page()."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "RSeries")
        _assert_listall(wrapper, resource, "RSeries", page_result)

    @pytest.mark.parametrize("resource", _active(RSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_iterall(self, api, resource):
        """iterall(limit=25) yields at least one item without auto-paginating."""
        wrapper = getattr(api, resource["name"])
        _assert_iterall(wrapper, resource, "RSeries")

    @pytest.mark.parametrize("resource", _active(RSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_iter(self, api, resource):
        """iter(limit=25) yields items one at a time (R-Series specific generator)."""
        wrapper = getattr(api, resource["name"])
        items = list(wrapper.iter(limit=25))
        assert len(items) > 0, (
            f"RSeries.{resource['name']}.iter(limit=25) yielded no items"
        )
        _log("RSeries", resource["name"], "iter(limit=25)", items)


# ---------------------------------------------------------------------------
# C-Series
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_cseries
class TestCSeriesResources:
    """Live end-to-end tests for Lightspeed eCom (C-Series) resources."""

    @pytest.fixture(scope="class")
    def api(self):
        return LightspeedCSeriesApi(**_cseries_creds())

    @pytest.mark.parametrize("resource", _active(CSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_page(self, api, resource):
        """page() returns a non-empty list."""
        _assert_page(getattr(api, resource["name"]), resource, "CSeries")

    @pytest.mark.parametrize("resource", _active(CSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_get(self, api, resource):
        """get(id) returns the individual record."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "CSeries")
        _assert_get(wrapper, resource, "CSeries", page_result)

    @pytest.mark.parametrize("resource", _active(CSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_listall(self, api, resource):
        """listall() returns at least as many records as page()."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "CSeries")
        _assert_listall(wrapper, resource, "CSeries", page_result)

    @pytest.mark.parametrize("resource", _active(CSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_iterall(self, api, resource):
        """iterall(limit=25) yields at least one item."""
        wrapper = getattr(api, resource["name"])
        _assert_iterall(wrapper, resource, "CSeries")

    @pytest.mark.parametrize(
        "resource",
        [r for r in _active(CSERIES_RESOURCES) if r["has_count"]],
        ids=lambda r: r["name"],
    )
    def test_count(self, api, resource):
        """count() returns a non-negative integer (C-Series /count endpoint)."""
        wrapper = getattr(api, resource["name"])
        _assert_count(wrapper, resource, "CSeries")


# ---------------------------------------------------------------------------
# X-Series
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_xseries
class TestXSeriesResources:
    """Live end-to-end tests for Lightspeed Retail X-Series resources."""

    @pytest.fixture(scope="class")
    def api(self):
        return LightspeedXSeriesApi(**_xseries_creds())

    @pytest.mark.parametrize("resource", _active(XSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_page(self, api, resource):
        """page() returns a non-empty list."""
        _assert_page(getattr(api, resource["name"]), resource, "XSeries")

    @pytest.mark.parametrize("resource", _active(XSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_get(self, api, resource):
        """get(id) returns the individual record."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "XSeries")
        _assert_get(wrapper, resource, "XSeries", page_result)

    @pytest.mark.parametrize("resource", _active(XSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_listall(self, api, resource):
        """listall() returns at least as many records as page()."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "XSeries")
        _assert_listall(wrapper, resource, "XSeries", page_result)

    @pytest.mark.parametrize("resource", _active(XSERIES_RESOURCES), ids=lambda r: r["name"])
    def test_iterall(self, api, resource):
        """iterall(limit=25) yields at least one item."""
        wrapper = getattr(api, resource["name"])
        _assert_iterall(wrapper, resource, "XSeries")


# ---------------------------------------------------------------------------
# E-Series
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_eseries
class TestESeriesResources:
    """Live end-to-end tests for Lightspeed eCom E-Series (Ecwid) resources."""

    @pytest.fixture(scope="class")
    def api(self):
        return LightspeedESeriesApi(**_eseries_creds())

    @pytest.mark.parametrize("resource", _active(ESERIES_RESOURCES), ids=lambda r: r["name"])
    def test_page(self, api, resource):
        """page() returns a non-empty list."""
        _assert_page(getattr(api, resource["name"]), resource, "ESeries")

    @pytest.mark.parametrize("resource", _active(ESERIES_RESOURCES), ids=lambda r: r["name"])
    def test_get(self, api, resource):
        """get(id) returns the individual record."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "ESeries")
        _assert_get(wrapper, resource, "ESeries", page_result)

    @pytest.mark.parametrize("resource", _active(ESERIES_RESOURCES), ids=lambda r: r["name"])
    def test_listall(self, api, resource):
        """listall() returns at least as many records as page()."""
        wrapper = getattr(api, resource["name"])
        page_result = _assert_page(wrapper, resource, "ESeries")
        _assert_listall(wrapper, resource, "ESeries", page_result)

    @pytest.mark.parametrize("resource", _active(ESERIES_RESOURCES), ids=lambda r: r["name"])
    def test_iterall(self, api, resource):
        """iterall(limit=25) yields at least one item."""
        wrapper = getattr(api, resource["name"])
        _assert_iterall(wrapper, resource, "ESeries")
