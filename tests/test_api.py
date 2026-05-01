"""
Tests for pylightspeed API client instantiation.

These tests verify that each series API class correctly:
- Sets the namespace and timestamp field names
- Builds the right Connection type with the right credentials
- Uses the correct host and auth mechanism

Authentication patterns by series:
- C-Series (eCom):  basic auth — api_key + api_secret stored as _session.auth tuple
- R-Series (Retail): OAuth bearer token — token_file holds access_token + refresh_token JSON
- X-Series (Retail): personal token — Bearer token set in _session.headers["authorization"]
- E-Series (eCom):  store ID + api_secret basic auth (Ecwid-style)

R-Series note: _manage_token_refresh() always POSTs to the access_token_url on init
(self.expires == 0).  Tests patch pylightspeed.connection.requests.post so no real
network call is made, and the refreshed token is predictable.
"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from pylightspeed.api import (
    LightspeedCSeriesApi,
    LightspeedRSeriesApi,
    LightspeedXSeriesApi,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

REFRESHED_TOKEN = "refreshed_access_token_abc123"
REFRESHED_REFRESH = "refreshed_refresh_token_xyz789"


@pytest.fixture
def token_file(tmp_path):
    """Write a minimal valid R-Series token file and return its path.

    The file needs a refresh_token so _manage_token_refresh() can build the
    refresh POST payload.  The actual access_token in the file is overwritten
    by the mock POST response (see mock_token_post fixture).
    """
    codes = {
        "access_token": "stale_access_token",
        "expires_in": 3600,
        "token_type": "bearer",
        "scope": "employee:all",
        "refresh_token": "stored_refresh_token_xyz789",
        "last_run": time.time() - 7200,  # 2 hours ago — token is expired
    }
    f = tmp_path / "test_codes.json"
    f.write_text(json.dumps(codes))
    return str(f)


@pytest.fixture
def mock_token_post():
    """Patch requests.post inside the connection module.

    _manage_token_refresh() calls requests.post() to exchange the refresh token
    for a new access token.  This fixture returns a canned valid response so
    that no real HTTP call is made and the resulting access_token is known.
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": REFRESHED_TOKEN,
        "token_type": "bearer",
        "scope": "employee:all",
        "expires_in": 3600,
        # Lightspeed ALWAYS issues a new refresh_token on every refresh and
        # immediately revokes the old one.  The connection must save this new
        # refresh_token, not the old one from the token store.
        "refresh_token": REFRESHED_REFRESH,
    }
    with patch("pylightspeed.connection.requests.post", return_value=mock_response):
        yield mock_response


class TestLightspeedCSeriesApi:
    """C-Series uses basic auth: api_key + api_secret."""

    def test_namespace(self):
        api = LightspeedCSeriesApi(api_key="test_key", api_secret="test_secret")
        assert api.namespace == "CSeries"

    def test_timestamp_fields(self):
        api = LightspeedCSeriesApi(api_key="test_key", api_secret="test_secret")
        assert api.created_at == "createdAt"
        assert api.updated_at == "updatedAt"

    def test_default_host(self):
        api = LightspeedCSeriesApi(api_key="test_key", api_secret="test_secret")
        assert api.connection.host == "api.shoplightspeed.com"

    def test_session_auth_tuple(self):
        """Auth is stored as a (key, secret) tuple on the requests Session."""
        api = LightspeedCSeriesApi(api_key="my_key", api_secret="my_secret")
        assert api.connection._session.auth == ("my_key", "my_secret")

    def test_basic_auth_tuple_equivalent(self):
        """Passing basic_auth tuple directly is equivalent to api_key + api_secret."""
        api1 = LightspeedCSeriesApi(api_key="k", api_secret="s")
        api2 = LightspeedCSeriesApi(basic_auth=("k", "s"))
        assert api1.connection._session.auth == api2.connection._session.auth

    def test_custom_host(self):
        api = LightspeedCSeriesApi(
            host="api.shoplightspeed.com",
            api_key="k",
            api_secret="s",
            api_path="/au/{}",
        )
        assert api.connection.host == "api.shoplightspeed.com"
        assert "/au/" in api.connection.api_path


class TestLightspeedRSeriesApi:
    """R-Series uses OAuth with a bearer token stored in a local JSON file.

    All tests in this class receive the mock_token_post fixture, which patches
    requests.post so _manage_token_refresh() never hits the network.  After
    init the connection's access_token equals REFRESHED_TOKEN (the value
    returned by the mock POST response).
    """

    def test_namespace(self, mock_token_post, token_file):
        api = LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        assert api.namespace == "RSeries"

    def test_timestamp_fields(self, mock_token_post, token_file):
        api = LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        assert api.created_at == "createTime"
        assert api.updated_at == "timeStamp"

    def test_connection_credentials(self, mock_token_post, token_file):
        api = LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        assert api.connection.account_id == "190211"
        assert api.connection.client_id == "test_client_id"
        assert api.connection.client_secret == "test_client_secret"
        assert api.connection.token_file == token_file

    def test_access_token_set_after_refresh(self, mock_token_post, token_file):
        """After init the connection.access_token equals the value from the mock POST."""
        api = LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        assert api.connection.access_token == REFRESHED_TOKEN

    def test_new_refresh_token_saved_after_refresh(self, mock_token_post, token_file):
        """The NEW refresh_token from the OAuth response must be persisted.

        Lightspeed issues a brand-new refresh_token on every refresh and
        immediately revokes the old one.  Any code that re-saves the *old*
        refresh_token will cause the next refresh to fail with invalid_grant.
        """
        LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        with open(token_file) as f:
            saved = json.load(f)
        assert saved["refresh_token"] == REFRESHED_REFRESH, (
            "Token store must hold the NEW refresh_token issued by Lightspeed, "
            "not the stale one from the previous token store."
        )

    def test_bearer_token_in_session_headers(self, mock_token_post, token_file):
        """The OAuth bearer token should be set in the session Authorization header."""
        api = LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        auth_header = api.connection._session.headers.get("authorization", "")
        assert REFRESHED_TOKEN in auth_header

    def test_default_host(self, mock_token_post, token_file):
        api = LightspeedRSeriesApi(
            account_id="190211",
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_file=token_file,
        )
        assert api.connection.host == "api.lightspeedapp.com"


class TestLightspeedXSeriesApi:
    """X-Series uses a Personal Access Token sent as a Bearer header."""

    def test_namespace(self):
        api = LightspeedXSeriesApi(
            domain_prefix="mystore", personal_token="my_personal_token"
        )
        assert api.namespace == "XSeries"

    def test_timestamp_fields(self):
        api = LightspeedXSeriesApi(
            domain_prefix="mystore", personal_token="my_personal_token"
        )
        assert api.created_at == "created_at"
        assert api.updated_at == "updated_at"

    def test_host_includes_domain_prefix(self):
        api = LightspeedXSeriesApi(
            domain_prefix="mystore", personal_token="my_personal_token"
        )
        assert "mystore" in api.connection.host

    def test_bearer_token_in_session_headers(self):
        """Personal token must appear as a Bearer token in the session headers."""
        api = LightspeedXSeriesApi(
            domain_prefix="mystore", personal_token="my_personal_token"
        )
        auth_header = api.connection._session.headers.get("authorization", "")
        assert "Bearer my_personal_token" == auth_header

    def test_missing_credentials_raises(self):
        """Providing a domain_prefix with no token or OAuth creds should raise."""
        with pytest.raises(Exception):
            LightspeedXSeriesApi(domain_prefix="mystore")
