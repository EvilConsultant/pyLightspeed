"""
Integration tests — these call the *live* Lightspeed API.

Credentials are read from environment variables.  Populate the repo's .env
file (or export the vars in your shell) before running.  Every test is
automatically skipped when its required variables are absent, so the full
test suite remains green in CI with no credentials.

Run only integration tests:
    pytest -m integration -v

Skip them (default behaviour in CI):
    pytest -m "not integration"

Required .env variables
-----------------------
R-Series (OAuth retail API):
    LSR_ACCOUNT_ID      e.g. 190211
    LSR_CLIENT_ID       OAuth client_id from Lightspeed developer portal
    LSR_CLIENT_SECRET   OAuth client_secret
    LSR_TOKEN_FILE      Absolute path to the JSON codes file, e.g.
                        C:/Data/Development/BottleAdmin/bottleadmin/.codes/vintage_codes.json

C-Series (eCom API, basic auth):
    LSC_API_KEY         API key from Lightspeed eCom back-office
    LSC_API_SECRET      API secret
    LSC_API_HOST        (optional) defaults to api.shoplightspeed.com
    LSC_API_PATH        (optional) defaults to /us/{}
"""

import os
import pytest

# Load .env from the repo root if present.  python-dotenv is a dev dependency.
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # No dotenv installed — rely on shell environment

from pylightspeed.api import LightspeedRSeriesApi, LightspeedCSeriesApi


# ---------------------------------------------------------------------------
# Credential helpers / skip guards
# ---------------------------------------------------------------------------

def _rseries_creds():
    """Return R-Series credentials from env, or None if any are missing."""
    account_id = os.environ.get("LSR_ACCOUNT_ID")
    client_id = os.environ.get("LSR_CLIENT_ID")
    client_secret = os.environ.get("LSR_CLIENT_SECRET")
    token_file = os.environ.get("LSR_TOKEN_FILE")
    if not all([account_id, client_id, client_secret, token_file]):
        return None
    return {
        "account_id": account_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "token_file": token_file,
    }


def _cseries_creds():
    """Return C-Series credentials from env, or None if any are missing."""
    api_key = os.environ.get("LSC_API_KEY")
    api_secret = os.environ.get("LSC_API_SECRET")
    if not all([api_key, api_secret]):
        return None
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "host": os.environ.get("LSC_API_HOST", "api.shoplightspeed.com"),
        "api_path": os.environ.get("LSC_API_PATH", "/us/{}"),
    }


requires_rseries = pytest.mark.skipif(
    _rseries_creds() is None,
    reason="LSR_* credentials not set in environment / .env",
)

requires_cseries = pytest.mark.skipif(
    _cseries_creds() is None,
    reason="LSC_* credentials not set in environment / .env",
)


# ---------------------------------------------------------------------------
# R-Series integration tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@requires_rseries
class TestRSeriesLive:
    """Smoke tests against the live Lightspeed Retail (R-Series) API."""

    @pytest.fixture(scope="class")
    def rseries_api(self):
        """Build a real RSeriesApi instance using credentials from .env."""
        creds = _rseries_creds()
        return LightspeedRSeriesApi(**creds)

    def test_employee_page_returns_results(self, rseries_api):
        """Employees.page() should return at least one employee record."""
        employees = rseries_api.Employees.page()
        assert isinstance(employees, list), "Expected a list of employees"
        assert len(employees) > 0, "Expected at least one employee"

    def test_employee_has_expected_fields(self, rseries_api):
        """Each employee record should have an employeeID and firstName."""
        employees = rseries_api.Employees.page()
        first = employees[0]
        assert "employeeID" in first, f"Missing employeeID in: {first.keys()}"
        assert "firstName" in first, f"Missing firstName in: {first.keys()}"

    def test_employee_listall_returns_all(self, rseries_api):
        """Employees.listall() should return at least as many results as a single page."""
        page = rseries_api.Employees.page()
        all_employees = rseries_api.Employees.listall()
        assert len(all_employees) >= len(page), (
            f"listall() returned {len(all_employees)} but page() returned {len(page)}"
        )


# ---------------------------------------------------------------------------
# C-Series integration tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@requires_cseries
class TestCSeriesLive:
    """Smoke tests against the live Lightspeed eCom (C-Series) API."""

    @pytest.fixture(scope="class")
    def cseries_api(self):
        """Build a real CSeriesApi instance using credentials from .env."""
        creds = _cseries_creds()
        return LightspeedCSeriesApi(**creds)

    def test_filters_page_returns_results(self, cseries_api):
        """Filters.page() should return at least one filter."""
        filters = cseries_api.Filters.page()
        assert isinstance(filters, list), "Expected a list of filters"
        assert len(filters) > 0, "Expected at least one filter"

    def test_filters_have_expected_fields(self, cseries_api):
        """Each filter should have an id and title."""
        filters = cseries_api.Filters.page()
        first = filters[0]
        assert "id" in first, f"Missing id in: {first.keys()}"
        assert "title" in first, f"Missing title in: {first.keys()}"

    def test_filters_listall_at_least_as_large_as_page(self, cseries_api):
        """Filters.listall() should return at least as many records as a single page."""
        page = cseries_api.Filters.page()
        all_filters = cseries_api.Filters.listall()
        assert len(all_filters) >= len(page), (
            f"listall() returned {len(all_filters)} but page() returned {len(page)}"
        )
