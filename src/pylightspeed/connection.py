"""
Connection Objects
==================

Handles the lower-level details of the API: making requests, managing responses,
token storage, and rate limits.

The high-level API (`pylightspeed.api.LightspeedApi`) wraps a lower-level connection
from this module, accessible via `api.connection`. It provides helper methods for
`get`/`post`/`put`/`delete` operations.

Each Lightspeed API series has a different authentication and rate-limiting approach,
so `Connection` is subclassed for each series.

Note:
    While pagination is often specific to an API or connection, pyLightspeed keeps
    pagination handling at the resource level to allow for more flexibility with
    resources/endpoints that have different pagination requirements based on version
    or other factors.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from decimal import Decimal
import base64
import hashlib
import os
import secrets
import tempfile
import threading

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import requests
import json
import time
from time import sleep

from .exceptions import *

from loguru import logger
logger = logger.bind(module="pylightspeed.connection")

logger.debug("connection module loaded")


# Handle Decimal types in JSON, see: https://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


# ---------------------------------------------------------------------------
# Cross-process token refresh locking
# ---------------------------------------------------------------------------
# Per lock-path threading.Locks — created lazily, never released (cheap).
_process_locks: dict[str, threading.Lock] = {}
_process_lock_meta = threading.Lock()


@contextmanager
def _file_lock(lock_path: str, timeout: float = 30.0, stale_after: float = 60.0):
    """Exclusive cross-process lock backed by a lock file.

    Also acquires a per-path :class:`~threading.Lock` so threads within the
    same process queue up rather than racing each other.

    The lock file is created atomically with ``os.O_CREAT | os.O_EXCL`` —
    atomic on both Linux and Windows.  If the file already exists and is
    older than *stale_after* seconds (the holder process crashed), it is
    removed and the attempt retried.  Polls every 100 ms until *timeout*
    seconds have elapsed, then raises :exc:`TimeoutError`.
    """
    with _process_lock_meta:
        if lock_path not in _process_locks:
            _process_locks[lock_path] = threading.Lock()
    thread_lock = _process_locks[lock_path]

    with thread_lock:  # serialises threads within this process
        deadline = time.time() + timeout
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, str(os.getpid()).encode())
                finally:
                    os.close(fd)
                break  # lock acquired
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(lock_path) > stale_after:
                        os.unlink(lock_path)
                        continue  # retry immediately
                except OSError:
                    pass
                if time.time() >= deadline:
                    raise TimeoutError(
                        f"Could not acquire token refresh lock at {lock_path!r} "
                        f"within {timeout:.0f}s. If a .lock file remains from a "
                        f"crashed process, delete it manually."
                    )
                time.sleep(0.1)
        try:
            yield
        finally:
            try:
                os.unlink(lock_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Token Refresh Locking
# ---------------------------------------------------------------------------

class TokenLock(ABC):
    """Protocol for exclusive token refresh coordination.

    Implement :meth:`acquire` as a context manager that ensures only one
    caller at a time can check-and-refresh a token, regardless of how many
    threads or processes make the attempt simultaneously.

    Built-in implementations:

    * :class:`FileLock` — cross-process lock via ``O_CREAT|O_EXCL`` on a
      temp file.  Works on a single machine; default for all
      :class:`TokenStore` instances.
    * :class:`NullLock` — no-op; use when external infrastructure already
      guarantees single-writer access (e.g. a Hatchet workflow with
      ``concurrencyLimit=1``, or in tests).
    * :class:`VaultCASLock` — distributed lock backed by a dedicated Vault
      KV v2 key.  Used automatically by :class:`VaultTokenStore` so that
      any number of processes on any number of machines serialise token
      refresh correctly.
    """

    @abstractmethod
    @contextmanager
    def acquire(self, key: str, timeout: float = 30.0, stale_after: float = 15.0):
        """Acquire exclusive access keyed on *key*, yield, then release."""
        ...  # pragma: no cover


class FileLock(TokenLock):
    """Cross-process lock backed by a temp file.

    Uses ``os.O_CREAT | os.O_EXCL`` for atomic creation on both Linux and
    Windows.  Also acquires a per-path :class:`~threading.Lock` to serialise
    threads within the same process without redundant filesystem round-trips.
    Polls every 100 ms; files older than *stale_after* seconds (holder
    crashed) are removed automatically.
    """

    @contextmanager
    def acquire(self, key: str, timeout: float = 30.0, stale_after: float = 15.0):
        lock_name = hashlib.sha1(key.encode()).hexdigest()[:16]
        lock_path = os.path.join(
            tempfile.gettempdir(), f"pylightspeed_{lock_name}.lock"
        )
        with _file_lock(lock_path, timeout=timeout, stale_after=stale_after):
            yield


class NullLock(TokenLock):
    """No-op lock — provides no mutual exclusion.

    Use when surrounding infrastructure already guarantees single-writer
    semantics, or in unit tests where only one process runs.
    """

    @contextmanager
    def acquire(self, key: str, **kwargs):
        yield


# ---------------------------------------------------------------------------
# Token Storage
# ---------------------------------------------------------------------------

class TokenStore(ABC):
    """Abstract base class for OAuth token persistence.

    Implement :meth:`load` and :meth:`save` to persist and retrieve the
    rotating OAuth token.  Optionally implement :meth:`load_credentials` so
    that the API classes can pull static connection parameters (client ID,
    client secret, account ID, etc.) from the same backend, allowing a single
    store object to be the sole configuration source.

    Standard credential key names (used consistently across all built-in
    store implementations and the ``LightspeedXxxApi`` constructors):

    +----------------------+----------------------------------+
    | Key                  | Used for                         |
    +======================+==================================+
    | ``LSR_CLIENT_ID``    | R-Series OAuth client ID         |
    | ``LSR_CLIENT_SECRET``| R-Series OAuth client secret     |
    | ``LSR_ACCOUNT_ID``   | R-Series account / store ID      |
    | ``LSR_REDIRECT_URI`` | R-Series OAuth redirect URI      |
    | ``LSC_API_KEY``      | C-Series API key                 |
    | ``LSC_API_SECRET``   | C-Series API secret              |
    | ``LSX_DOMAIN_PREFIX``| X-Series domain prefix           |
    | ``LSX_PERSONAL_TOKEN``| X-Series personal access token  |
    +----------------------+----------------------------------+

    These names intentionally match the conventional ``.env`` variable names
    so that switching between file, MySQL, or Vault storage requires no
    credential renaming.
    """

    @abstractmethod
    def load_token(self) -> dict | None:
        """Return the stored token dict, or *None* if no token has been saved yet."""
        ...

    @abstractmethod
    def save_token(self, token_data: dict) -> None:
        """Persist *token_data* so it can be retrieved by a subsequent :meth:`load_token`."""
        ...

    def load_credentials(self) -> dict | None:
        """Return static connection credentials, or *None* if this store does not
        manage them.

        The returned dict should use the standard key names documented on
        :class:`TokenStore` (e.g. ``LSR_CLIENT_ID``, ``LSR_CLIENT_SECRET``).
        The ``LightspeedXxxApi`` constructors call this automatically when a
        *token_store* is provided; explicit constructor args always take
        precedence over values returned here.

        The default implementation returns *None* — override in subclasses
        that back static credentials.
        """
        return None

    @property
    def _lock(self) -> 'TokenLock':
        """The :class:`TokenLock` used to serialise token refresh calls.

        Defaults to :class:`FileLock` (cross-process on a single machine).
        Set ``self._lock = <lock>`` in a subclass ``__init__`` to install a
        different backend — e.g. :class:`VaultCASLock` for multi-machine
        deployments, or :class:`NullLock` when locking is handled elsewhere.
        """
        try:
            return self.__lock
        except AttributeError:
            self.__lock = FileLock()
            return self.__lock

    @_lock.setter
    def _lock(self, value: 'TokenLock') -> None:
        self.__lock = value

    def _lock_key(self) -> str:
        """Stable string that uniquely identifies this token's storage location.

        Passed as *key* to :meth:`TokenLock.acquire` so that all instances
        pointing at the same store share the same lock and serialise across
        processes.  Subclasses with a persistent identity (file path, Vault
        path, DB row key) should override this.

        The default uses class name + ``id(self)``, which only serialises
        threads within a single process — sufficient for stores with no
        stable cross-process identity (e.g. :class:`EnvTokenStore`).
        """
        return f"{self.__class__.__name__}_{id(self)}"

    def atomic_refresh(
        self,
        do_refresh_fn,
        expiry_buffer: int = 60,
        force: bool = False,
        stale_access_token: str | None = None,
    ) -> tuple[dict, bool]:
        """Refresh the token exactly once across all threads and processes.

        Acquires an exclusive lock via :attr:`_lock` (a :class:`TokenLock`),
        re-reads the token *under the lock*, and only calls *do_refresh_fn*
        if the token is still stale.  Any concurrent caller that waited for
        the lock will find the token already fresh on its re-read and return
        without calling the OAuth API — so the provider is called at most once
        regardless of how many processes race.

        The default lock is :class:`FileLock` (single machine).
        :class:`VaultTokenStore` installs a :class:`VaultCASLock` that
        extends this guarantee across any number of machines.

        Args:
            do_refresh_fn: ``(codes: dict) -> new_token_data: dict`` —
                exchanges the stored refresh token with the OAuth provider.
            expiry_buffer: Seconds before true expiry to treat as expired
                (default 60).

        Returns:
            ``(token_data, was_refreshed)`` — *was_refreshed* is ``True``
            only when this process called the OAuth API and saved the result.
        """
        with self._lock.acquire(self._lock_key()):
            # Re-read under the lock — a concurrent caller may have already
            # refreshed while we were waiting.
            codes = self.load_token()
            if codes is None:
                raise MissingTokenError(
                    f"No token found in {self!r}. Run the OAuth setup flow."
                )

            # FORCE / 401 path: the server has explicitly rejected an access token, so the local
            # expiry clock is NOT trustworthy (the token was revoked before its nominal expiry —
            # the classic refresh-token-rotation revocation). Before minting a new token, see if a
            # peer already replaced the one that failed: if the stored access token differs from the
            # one that 401'd, adopt the peer's token instead of refreshing again (avoids rotation
            # thrash where two consumers keep invalidating each other's tokens).
            if force and stale_access_token is not None:
                if codes.get("access_token") != stale_access_token:
                    logger.info(
                        f"atomic_refresh: a peer already replaced the failed token in {self!r} "
                        "— adopting it without refreshing."
                    )
                    return codes, False

            token_expires_at = codes.get("last_run", 0) + codes.get("expires_in", 0)
            clock_fresh = time.time() < token_expires_at - expiry_buffer
            # The clock short-circuit is correct ONLY when not forcing: it prevents a double
            # refresh when a peer just refreshed. On a 401 (force=True) we MUST refresh regardless
            # of the clock — trusting the clock here is exactly the bug that let dead-but-"valid"
            # tokens be reused, so the retry 401'd again.
            if clock_fresh and not force:
                logger.debug(
                    f"atomic_refresh: token in {self!r} already fresh "
                    f"({token_expires_at - time.time():.0f}s remaining) — "
                    "another process already refreshed."
                )
                return codes, False

            if force:
                logger.info(
                    f"atomic_refresh: FORCING refresh in {self!r} after a 401 — server rejected "
                    "the token regardless of the local clock."
                )
            new_token_data = do_refresh_fn(codes)
            self.save_token(new_token_data)
            return new_token_data, True


class FileTokenStore(TokenStore):
    """Stores OAuth tokens in a local JSON file using atomic writes.

    Atomic writes (write to a temp file, then `os.replace`) prevent
    credential-file corruption if the process is interrupted mid-write.

    Optionally accepts a separate *credentials_file* so that static
    connection parameters (client ID, secret, account ID, etc.) can be
    co-located with the token store rather than scattered across ``.env``
    variables or hard-coded constructor arguments. The credentials file is
    never modified by :meth:`save` — only the token file is written.

    Args:
        path (str): Absolute or relative path to the token JSON file.
        credentials_file (str | None): Path to a JSON file containing static
            credentials keyed by the standard names (``LSR_CLIENT_ID``,
            ``LSR_CLIENT_SECRET``, etc.; see :class:`TokenStore`). When
            provided, :meth:`load_credentials` reads and returns that file.
    """

    def __init__(self, path: str, credentials_file: str | None = None):
        self.path = path
        self.credentials_file = credentials_file

    def load_token(self) -> dict | None:
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save_token(self, token_data: dict) -> None:
        dir_ = os.path.dirname(os.path.abspath(self.path))
        fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(token_data, f, indent=4)
            os.replace(tmp_path, self.path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load_credentials(self) -> dict | None:
        """Return credentials from *credentials_file*, or *None* if not configured."""
        if self.credentials_file is None:
            return None
        try:
            with open(self.credentials_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def __repr__(self) -> str:
        if self.credentials_file:
            return f"FileTokenStore(path={self.path!r}, credentials_file={self.credentials_file!r})"
        return f"FileTokenStore(path={self.path!r})"

    def _lock_key(self) -> str:
        return os.path.abspath(self.path)


class MySQLTokenStore(TokenStore):
    """Base class for storing OAuth tokens in a MySQL database via SQLAlchemy.

    Handles connection management only.  Subclass this and implement
    :meth:`load` and :meth:`save` to match your own table structure.

    All database operations use SQLAlchemy Core with the
    ``mysql+mysqlconnector`` dialect so no separate DB-API driver import is
    needed beyond what SQLAlchemy already expects.

    Connection parameters default to the standard ``MYSQL_*`` environment
    variables, so no extra configuration is needed when running inside
    apps that already set those vars.

    Args:
        host (str | None): MySQL host.  Defaults to ``MYSQL_HOST`` env var or
            ``"127.0.0.1"``.
        port (int | None): MySQL port.  Defaults to ``MYSQL_PORT`` env var or
            ``3306``.
        user (str | None): MySQL user.  Defaults to ``MYSQL_USER`` env var or
            ``"root"``.
        password (str | None): MySQL password.  Defaults to ``MYSQL_PASSWORD``
            env var or ``""``.
        database (str | None): MySQL database name.  Defaults to ``MYSQL_DB``
            env var or ``"bottleadmin"``.

    Requires:
        ``sqlalchemy`` and ``mysql-connector-python`` — install with
        ``uv add 'pylightspeed[mysql]'``.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ):
        self._host = host or os.getenv("MYSQL_HOST", "127.0.0.1")
        self._port = int(port or os.getenv("MYSQL_PORT", "3306"))
        self._user = user or os.getenv("MYSQL_USER", "root")
        self._password = password or os.getenv("MYSQL_PASSWORD", "")
        self._database = database or os.getenv("MYSQL_DB", "bottleadmin")

    def _engine(self):
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise ImportError(
                "MySQLTokenStore requires sqlalchemy and mysql-connector-python. "
                "Install with: uv add 'pylightspeed[mysql]'"
            ) from exc
        url = (
            f"mysql+mysqlconnector://{self._user}:{self._password}"
            f"@{self._host}:{self._port}/{self._database}"
        )
        return create_engine(url, pool_pre_ping=True)

    def load_token(self) -> dict | None:
        raise NotImplementedError

    def save_token(self, token_data: dict) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"db={self._database!r}@{self._host}:{self._port})"
        )


class StoresTableTokenStore(MySQLTokenStore):
    """Stores OAuth tokens in a JSON column on a ``stores`` table.

    This is an example MySQL token store implementation — adapt it to your own
    schema or use it as-is if your database has a ``stores`` table with an
    ``id`` primary key and a ``config`` JSON column.

    The token dict is persisted as the value of *config_key* inside the
    ``config`` JSON column on the row identified by *store_id*.  All other
    keys in ``config`` are preserved — only the token key is touched.

    This lets multiple apps share a single token that auto-refreshes in place
    without any file-system coordination.

    Optionally supply *credentials_config_key* to store static connection
    credentials (``LSR_CLIENT_ID``, ``LSR_CLIENT_SECRET``, etc.) in a
    *separate* JSON key on the same row.  When set, :meth:`load_credentials`
    reads and returns that key.

    Args:
        store_id (int): The ``stores.id`` value whose config holds the token.
        config_key (str): JSON key within ``stores.config`` to write the token
            under.  Defaults to ``"LSRETAIL_TOKEN"``.
        credentials_config_key (str | None): JSON key within ``stores.config``
            holding static credentials (see :class:`TokenStore` for key names).
            When *None* (default), :meth:`load_credentials` returns *None*.
        host (str | None): See :class:`MySQLTokenStore`.
        port (int | None): See :class:`MySQLTokenStore`.
        user (str | None): See :class:`MySQLTokenStore`.
        password (str | None): See :class:`MySQLTokenStore`.
        database (str | None): See :class:`MySQLTokenStore`.
    """

    def __init__(
        self,
        store_id: int,
        config_key: str = "LSRETAIL_TOKEN",
        credentials_config_key: str | None = None,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ):
        super().__init__(host=host, port=port, user=user, password=password, database=database)
        self.store_id = store_id
        self.config_key = config_key
        self.credentials_config_key = credentials_config_key

    def _read_config_key(self, key: str) -> dict | None:
        """Read a single JSON key from stores.config for this store_id."""
        from sqlalchemy import text
        with self._engine().connect() as conn:
            row = conn.execute(
                text("SELECT JSON_EXTRACT(config, :key) AS val FROM stores WHERE id = :id"),
                {"key": f"$.{key}", "id": self.store_id},
            ).mappings().fetchone()
        if row is None:
            raise RuntimeError(
                f"StoresTableTokenStore: no stores row for id={self.store_id}"
            )
        raw = row["val"]
        if raw is None:
            return None
        return json.loads(raw) if isinstance(raw, str) else raw

    def load_token(self) -> dict | None:
        return self._read_config_key(self.config_key)

    def save_token(self, token_data: dict) -> None:
        from sqlalchemy import text
        with self._engine().begin() as conn:
            conn.execute(
                text(
                    "UPDATE stores "
                    "SET config = JSON_SET(COALESCE(config, '{}'), :key, CAST(:val AS JSON)) "
                    "WHERE id = :id"
                ),
                {
                    "key": f"$.{self.config_key}",
                    "val": json.dumps(token_data),
                    "id": self.store_id,
                },
            )

    def load_credentials(self) -> dict | None:
        """Return credentials from *credentials_config_key*, or *None* if not configured."""
        if self.credentials_config_key is None:
            return None
        return self._read_config_key(self.credentials_config_key)

    def __repr__(self) -> str:
        return (
            f"StoresTableTokenStore(store_id={self.store_id!r}, "
            f"config_key={self.config_key!r}, "
            f"db={self._database!r}@{self._host}:{self._port})"
        )


class VaultCASLock(TokenLock):
    """Distributed lock backed by a dedicated Vault KV v2 key.

    Uses CAS (check-and-set) writes so that the lock acquisition is atomic
    server-side — exactly one caller across all machines succeeds; all
    others spin and retry.

    **Algorithm**

    *Acquire*: Read the lock key and its current version.  If the holder
    field is absent or ``null``, or the entry is older than *stale_after*
    seconds (the holder crashed), attempt a CAS write with the current
    version.  If the CAS succeeds ownership is granted.  If it fails
    (another machine wrote first), poll every 100 ms and retry.

    *Release*: Write ``{"holder": null}`` without CAS — only the holder
    calls release, so no conflict is possible.

    Args:
        lock_path: KV v2 path used exclusively as the mutex key.  Must be
            different from any token or credentials path.  Convention:
            ``token_path + "_lock"``
            (e.g. ``"lightspeed/stores/1/token_lock"``).
        vault_addr: Vault URL.  Defaults to the ``VAULT_ADDR`` env var.
        vault_token: Vault token.  Defaults to the ``VAULT_TOKEN`` env var.
        mount_point: KV v2 mount point (default ``"secret"``).

    Requires:
        ``hvac`` — install with ``uv add 'pylightspeed[vault]'``.
    """

    def __init__(
        self,
        lock_path: str,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        mount_point: str = "secret",
    ):
        self.lock_path = lock_path
        self._vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self._vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point

    def _client(self):
        try:
            import hvac
        except ImportError as exc:
            raise ImportError(
                "VaultCASLock requires hvac. "
                "Install with: uv add 'pylightspeed[vault]'"
            ) from exc
        client = hvac.Client(url=self._vault_addr, token=self._vault_token)
        if not client.is_authenticated():
            raise RuntimeError(
                "VaultCASLock: Vault client is not authenticated. "
                "Check VAULT_ADDR and VAULT_TOKEN environment variables."
            )
        return client

    def _read_with_version(self) -> tuple[dict | None, int]:
        try:
            response = self._client().secrets.kv.v2.read_secret_version(
                path=self.lock_path,
                mount_point=self.mount_point,
                raise_on_deleted_version=True,
            )
            return response["data"]["data"], response["data"]["metadata"]["version"]
        except Exception as exc:
            if "InvalidPath" in type(exc).__name__ or "404" in str(exc):
                return None, 0
            raise

    @contextmanager
    def acquire(self, key: str, timeout: float = 30.0, stale_after: float = 15.0):
        """Acquire the Vault distributed lock, yield, then release.

        The *key* argument is accepted for protocol compatibility but ignored
        — :class:`VaultCASLock` uses :attr:`lock_path` as its identity, which
        is set at construction time.

        Also acquires a per-path :class:`~threading.Lock` first so that
        threads within the same process serialise without redundant Vault
        round-trips.
        """
        import socket

        # In-process thread serialisation — prevents redundant Vault calls
        # from concurrent threads within the same process.
        with _process_lock_meta:
            if self.lock_path not in _process_locks:
                _process_locks[self.lock_path] = threading.Lock()
        thread_lock = _process_locks[self.lock_path]

        with thread_lock:
            holder_id = f"{os.getpid()}@{socket.gethostname()}"
            deadline = time.time() + timeout

            while True:
                data, version = self._read_with_version()
                is_free = data is None or data.get("holder") is None
                is_stale = (
                    not is_free
                    and time.time() - (data.get("acquired_at") or 0) > stale_after
                )
                if is_free or is_stale:
                    try:
                        self._client().secrets.kv.v2.create_or_update_secret(
                            path=self.lock_path,
                            secret={"holder": holder_id, "acquired_at": time.time()},
                            mount_point=self.mount_point,
                            cas=version,
                        )
                        break  # acquired
                    except Exception as exc:
                        cas_conflict = (
                            "InvalidRequest" in type(exc).__name__
                            or "check-and-set" in str(exc).lower()
                            or "cas" in str(exc).lower()
                        )
                        if not cas_conflict:
                            raise
                        # Another machine got there first — fall through to retry

                if time.time() >= deadline:
                    raise TimeoutError(
                        f"Could not acquire Vault distributed lock at "
                        f"{self.lock_path!r} within {timeout:.0f}s."
                    )
                time.sleep(0.1)

            try:
                yield
            finally:
                try:
                    self._client().secrets.kv.v2.create_or_update_secret(
                        path=self.lock_path,
                        secret={"holder": None},
                        mount_point=self.mount_point,
                    )
                except Exception:
                    pass  # best-effort; stale detection covers crashes


class VaultTokenStore(TokenStore):
    """Stores OAuth tokens in HashiCorp Vault (KV v2 secrets engine).

    Manages both the rotating OAuth token and, optionally, the static
    connection credentials (client ID, secret, account ID, etc.) when
    *credentials_path* is provided.  This allows a single
    ``VaultTokenStore`` instance to be the complete configuration source
    for a ``LightspeedXxxApi`` constructor.

    The token is read and written at *token_path* — a single path that
    owns the full token object (access token, refresh token, expiry).

    Credentials are read-only static config that may be spread across
    multiple Vault paths.  Pass a list to *credentials_path* and the
    results are merged left-to-right, so later paths (e.g. store-specific)
    override earlier ones (e.g. shared).  The merged result is cached
    after the first call to :meth:`load_credentials`.

    Args:
        token_path (str): KV v2 path for the OAuth token secret —
            used for both reading and writing
            (e.g. ``"lightspeed/stores/2"``).  Required.
        credentials_path (str | list[str] | None): One path or an ordered
            list of paths holding static connection credentials keyed by
            the standard names (e.g.
            ``["lightspeed/shared", "lightspeed/stores/2"]``).  Paths are
            merged left-to-right so later entries override earlier ones.
            When *None*, :meth:`load_credentials` returns *None*.
        vault_addr (str | None): Vault server URL.  Defaults to the
            ``VAULT_ADDR`` environment variable.
        vault_token (str | None): Vault authentication token.  Defaults to
            the ``VAULT_TOKEN`` environment variable.
        mount_point (str): KV v2 mount point.  Defaults to ``"secret"``.

    Requires:
        ``hvac`` — install with ``uv add 'pylightspeed[vault]'``.
    """

    def __init__(
        self,
        token_path: str,
        credentials_path: str | list[str] | None = None,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        mount_point: str = "secret",
    ):
        # Guard: token_path and credentials_path must not overlap — writing a
        # token to the same Vault path that holds credentials would silently
        # replace them, since KV v2 create_or_update_secret overwrites the
        # entire secret.
        if credentials_path is not None:
            cred_paths = (
                [credentials_path]
                if isinstance(credentials_path, str)
                else list(credentials_path)
            )
            if token_path in cred_paths:
                raise ValueError(
                    f"VaultTokenStore: token_path {token_path!r} must not be the same as "
                    f"any credentials_path entry — saving a token would overwrite your "
                    f"credentials.  Use separate Vault paths for tokens and credentials "
                    f"(e.g. 'lightspeed/stores/2/tokens' vs 'lightspeed/stores/2/creds')."
                )

        self.token_path = token_path
        self.credentials_path = credentials_path
        self._vault_addr = vault_addr or os.getenv("VAULT_ADDR")
        self._vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point
        self._credentials_cache: dict | None = None
        self._credentials_loaded: bool = False
        # Install a Vault distributed lock so that any number of processes
        # on any number of machines serialise token refresh correctly.
        # A dedicated lock path avoids interfering with the token secret.
        self._lock = VaultCASLock(
            lock_path=token_path + "_lock",
            vault_addr=self._vault_addr,
            vault_token=self._vault_token,
            mount_point=mount_point,
        )

    def _client(self):
        try:
            import hvac
        except ImportError as exc:
            raise ImportError(
                "VaultTokenStore requires hvac. "
                "Install with: uv add 'pylightspeed[vault]'"
            ) from exc
        client = hvac.Client(url=self._vault_addr, token=self._vault_token)
        if not client.is_authenticated():
            raise RuntimeError(
                "VaultTokenStore: Vault client is not authenticated. "
                "Check VAULT_ADDR and VAULT_TOKEN environment variables."
            )
        return client

    def _read_path(self, path: str) -> dict | None:
        """Read a KV v2 secret at *path*, returning its data dict or None."""
        import hvac.exceptions
        try:
            response = self._client().secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point,
                raise_on_deleted_version=True,
            )
            return response["data"]["data"]
        except Exception as exc:
            # hvac raises InvalidPath when the secret doesn't exist yet
            if "InvalidPath" in type(exc).__name__ or "404" in str(exc):
                return None
            raise

    def _read_path_with_version(self, path: str) -> tuple[dict | None, int]:
        """Read a KV v2 secret and return ``(data, version)``.

        *version* is 0 when the secret does not exist yet (first write).
        """
        try:
            response = self._client().secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point,
                raise_on_deleted_version=True,
            )
            return response["data"]["data"], response["data"]["metadata"]["version"]
        except Exception as exc:
            if "InvalidPath" in type(exc).__name__ or "404" in str(exc):
                return None, 0
            raise

    def load_token(self) -> dict | None:
        return self._read_path(self.token_path)

    def save_token(self, token_data: dict) -> None:
        self._client().secrets.kv.v2.create_or_update_secret(
            path=self.token_path,
            secret=token_data,
            mount_point=self.mount_point,
        )

    def _lock_key(self) -> str:
        return f"vault/{self.mount_point}/{self.token_path}"

    def load_credentials(self) -> dict | None:
        """Return credentials from *credentials_path*, or *None* if not configured.

        The result is cached after the first call — Vault is not queried
        again within the same process lifetime.
        """
        if not self.credentials_path:
            return None
        if not self._credentials_loaded:
            paths = (
                [self.credentials_path]
                if isinstance(self.credentials_path, str)
                else self.credentials_path
            )
            merged: dict = {}
            for p in paths:
                data = self._read_path(p)
                if data:
                    merged.update(data)
            self._credentials_cache = merged or None
            self._credentials_loaded = True
        return self._credentials_cache

    def __repr__(self) -> str:
        parts = [f"token_path={self.token_path!r}"]
        if self.credentials_path:
            parts.append(f"credentials_path={self.credentials_path!r}")
        parts.append(f"mount_point={self.mount_point!r}")
        return f"VaultTokenStore({', '.join(parts)})"


class EnvTokenStore(TokenStore):
    """Read-only token store backed by environment variables or an explicit dict.

    Useful as a credentials source in a :class:`CompositeTokenStore` when
    credentials already live in the process environment (e.g. loaded via
    ``python-dotenv``) without requiring a dedicated file or remote backend.

    All standard ``LSR_*``, ``LSC_*``, and ``LSX_*`` credential keys that are
    present in the source are returned by :meth:`load_credentials`.  Keys with
    empty or missing values are omitted.

    :meth:`load_token` always returns ``None`` — the environment is not a token
    store.  :meth:`save_token` raises :exc:`NotImplementedError` because the
    environment is read-only.

    Args:
        environ (dict | None): Explicit mapping to use instead of
            ``os.environ``.  Useful in tests or to pass a curated subset of keys.
    """

    _CREDENTIAL_KEYS: frozenset = frozenset({
        "LSR_CLIENT_ID", "LSR_CLIENT_SECRET", "LSR_ACCOUNT_ID", "LSR_REDIRECT_URI",
        "LSC_API_KEY", "LSC_API_SECRET", "LSC_API_HOST", "LSC_API_PATH",
        "LSX_DOMAIN_PREFIX", "LSX_PERSONAL_TOKEN", "LSX_CLIENT_ID", "LSX_CLIENT_SECRET",
    })

    def __init__(self, environ: dict | None = None):
        self._environ = environ  # None → use os.environ at call time

    def load_token(self) -> dict | None:
        return None

    def save_token(self, token_data: dict) -> None:
        raise NotImplementedError(
            "EnvTokenStore is read-only.  "
            "Use a FileTokenStore, VaultTokenStore, or other writable store for tokens."
        )

    def load_credentials(self) -> dict | None:
        source = self._environ if self._environ is not None else os.environ
        result = {k: v for k in self._CREDENTIAL_KEYS if (v := source.get(k))}
        return result or None

    def __repr__(self) -> str:
        if self._environ is not None:
            return f"EnvTokenStore(keys={sorted(self._environ.keys())!r})"
        return "EnvTokenStore()"


class CompositeTokenStore(TokenStore):
    """Assembles credentials and token I/O from multiple independent stores.

    This is the primary composition point when credentials and tokens live in
    different backends, or when you want redundant token writes.

    **Credentials** are loaded from each store in *credentials* and merged
    left-to-right — later stores override earlier ones.

    **Token reads** are delegated to a single *token_read* store.

    **Token writes** are sent to every store in *token_write*.  Only stores
    explicitly listed receive the write — there is no implicit broadcasting.

    Args:
        credentials (TokenStore | list[TokenStore] | None): One or more stores
            whose :meth:`~TokenStore.load_credentials` results are merged L→R.
        token_read (TokenStore | None): Store used by :meth:`load_token`.
            When ``None``, :meth:`load_token` returns ``None``.
        token_write (TokenStore | list[TokenStore] | None): Store(s) written
            by :meth:`save_token`.  When ``None`` or empty,
            :meth:`save_token` raises :exc:`RuntimeError`.

    Example::

        store = CompositeTokenStore(
            credentials=[EnvTokenStore(), vault_store],
            token_read=vault_store,
            token_write=[vault_store, FileTokenStore("/tmp/backup.json")],
        )
        api = LightspeedRSeriesApi(token_store=store)
    """

    def __init__(
        self,
        credentials: "TokenStore | list[TokenStore] | None" = None,
        token_read: "TokenStore | None" = None,
        token_write: "TokenStore | list[TokenStore] | None" = None,
    ):
        if credentials is None:
            self._credential_stores: list = []
        elif isinstance(credentials, TokenStore):
            self._credential_stores = [credentials]
        else:
            self._credential_stores = list(credentials)

        self._token_read = token_read

        if token_write is None:
            self._token_write: list = []
        elif isinstance(token_write, TokenStore):
            self._token_write = [token_write]
        else:
            self._token_write = list(token_write)

    def load_token(self) -> dict | None:
        if self._token_read is None:
            return None
        return self._token_read.load_token()

    def save_token(self, token_data: dict) -> None:
        if not self._token_write:
            raise RuntimeError(
                "CompositeTokenStore: no token_write store configured.  "
                "Pass token_write=<store> when constructing CompositeTokenStore."
            )
        for store in self._token_write:
            store.save_token(token_data)

    def load_credentials(self) -> dict | None:
        merged: dict = {}
        for store in self._credential_stores:
            creds = store.load_credentials()
            if creds:
                merged.update(creds)
        return merged or None

    def __repr__(self) -> str:
        parts = []
        if self._credential_stores:
            parts.append(f"credentials={self._credential_stores!r}")
        if self._token_read is not None:
            parts.append(f"token_read={self._token_read!r}")
        if self._token_write:
            parts.append(f"token_write={self._token_write!r}")
        return f"CompositeTokenStore({', '.join(parts)})"


class Connection(object):
    """
    Connection class manages the connection handles the basics of making requests, handling responses, CRUD operations, and rate limits.
    The majority of the Connection class is intended to be fairly universal.
    """

    def __init__(self, host, auth, api_path="", format="json"):
        """Initializes the connection with the host, auth, and api_path.

        This only handles very simple APIs like Lightspeed C-Series. Build any API
        version or store IDs into *api_path* in the subclass ``__init__`` so that
        the final *api_path* passed here still contains ``{}`` as the resource
        placeholder used by `full_path`.

        Args:
            host (str): The base URL for the API (no scheme).
            auth (tuple): The authentication method — typically a ``(key, secret)``
                tuple passed to ``requests.Session.auth``.
            api_path (str): The URL path template; must contain ``{}`` so that
                the resource name can be interpolated by `full_path`.
            format (str): Response format extension, either ``'json'`` or ``'xml'``.
                Defaults to ``'json'``.
        """
        self.host = host
        # Note: api_path needs to be built such that it can be formatted with the resource name and id. For example, /en/Item/1234
        # To keep it consistent, build any api version or store ids into the api_path in the __init__ method of the connection
        # passing any api_path parameters from the API class to the connection class. Make sure the final api_path sent used to process
        # requests has the {} in it so that the resource name and id can be added to it by the full_path method.
        self.api_path = api_path
        # Lightspeed will return json or xml depending on extension. For simplicity, defining it at the object not method.
        self.format = format

        self.response = None
        self.resource = ""
        self.request_counter = 0

        self.timeout = 12.0  # need to catch timeout?

        logger.info("API Host: %s/%s" % (self.host, self.api_path))

        # Set up the Session using requests library and let the Session hold the auth and headers. See: https://2.python-requests.org/projects/3/user/advanced/#session-objects
        self._session = requests.Session()
        self._session.auth = auth

        # Leaving this in case header changes are needed later, but LSeCom needs no special header
        self._session.headers = {}

        self._last_response = None  # for debugging

    def full_path(self, url: str) -> str:
        """
        Constructs the full URL path for the given endpoint URL. This can be easily overridden by subclasses to handle different API paths.

        Args:
            url (str): The endpoint URL.

        Returns:
            str: The full URL path.

        Example:
            >>> connection = Connection()
            >>> connection.full_path('products')
            'https://example.com/api/v1/products.json'
        """
        return "https://" + self.host + self.api_path.format(url) + "." + self.format

    # Added files, which may cause problems with other methods
    def _run_method(
        self, method, url, data=None, query=None, headers=None, files=None, params=None
    ):
        """
        Executes a request to the API endpoing

        Args:
            method (str): The HTTP method to use for the request (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            url (str): The URL to send the request to.
            data (dict): The data or payload to send with the request. Note that other methods are processing data such as (name="thing") into a dict. However, if data contains a key "data", it will be passed raw to the request object.
            query (dict): The params included by requests in the URL. These are typically filters or other parameters that are passed in the URL.
            headers (dict): The headers to include in the request.
            files (dict): The files to upload with the request.
            params (dict): The additional parameters to include in the request.

        Returns:
            requests.Response: The response object returned by the API.

        Raises:
            requests.exceptions.RequestException: If an error occurs while making the request.
        """
        filter_string = ""
        # Build the final URL to LS expectations here, including appending JSON or XML
        if query is None:
            query = {}
        else:
            # if query contains "filter", remove it and create a new string
            # This is because the Lightspeed API has weird filters, and sometimes we just want to manually pass something in instead of using the parameters
            if "filter" in query:
                filter_string = query["filter"]
                del query["filter"]

        # Merge request-level headers with the session defaults.
        # Session headers (including the Bearer token) are used as the base;
        # any explicitly-passed headers take precedence.
        if headers is None:
            headers = dict(self._session.headers)
        elif "authorization" not in headers and self._session.headers.get("authorization"):
            headers["authorization"] = self._session.headers["authorization"]

        # If url is a fragment such as 'Item' or 'Item/5', build it into a full LS url. Or pass a full URL
        if url and url[:4] != "http":
            if (
                url[0] == "/"
            ):  # can call with '/resource' if you want, this will chop it off
                url = url[1:]
            url = self.full_path(url)
        elif not url:  # blank path
            url = self.full_path(url)

        qs = urlencode(query)
        if filter_string:
            if qs:
                qs = qs + "&" + filter_string
            else:
                qs = filter_string

        if qs:
            qs = "?" + qs
        url += qs

        # Is this needed? Should session not attach auth by itself if it is set at the connection._session.auth level?
        # Params - added to support E Series which passes tokens in the params
        # if self._session.params:
        #     if params:
        #         params.update(self._session.params)
        #     else:
        #         params = self._session.params

        # Process payloads.
        # If files are passed (like an Image), assume multipart/form-data and don't touch the data.
        if files:
            logger.debug(
                f"RUN METHOD w/IMAGES: {method} {url}\nDATA:{data}\nHEADERS:{headers}"
            )

            headers = {
                "Accept": "application/json",
                "authorization": self._session.headers.get("authorization"),
            }
            self._session.headers = headers  # Note, need to leave this because these headers are being picked up by the request, and unless cleared up, requests will not correctly attach the Content-Type form-data header
            # I have not researched this, but it seems that requests is using _session.headers not this explicit headers dict, and is attaching the Content-Type header for forms to the request
            # If you have problems here and forget what happened, inspect the headers in the request object and see if the Content-Type is set to form-data
            # and try r = requests.post(url, files=files, data=payload, headers=headers) to see if it works and what requests does with the headers
            return self._session.request(
                method,
                url,
                files=files,
                data=data,
                timeout=self.timeout,
                headers=headers,
            )
        # If no files, unpack any data and make sure headers are defaulted to JSON. Note you could override headers if you wanted to send XML.
        else:
            # data is normally being passed to the original create/update methods as title="thing", etc which is converted in to a dict
            # However, sometimes we need to pass params and data to the request object raw - for example with the E Series API batch endpoint
            # So let's inspect data for params and data keys, and if they exist, we will add them to the params and data dicts
            if (
                data and isinstance(data, dict)
            ):  # if data is just a string, assume it is just data and don't mess with it
                if data.get(
                    "params"
                ):  # params are being carried in the data dict by connection - probably need to unwind that so it handles params better. This is a quick fix.
                    if params:
                        params.update(data["params"])
                    else:
                        params = data["params"]
                    # delete the params key from the data dict so they don't get sent twice
                    del data["params"]

                # Added for e series batch, but moving here to get it out of the way of the files upload because R series files actually expects a payload with a data key
                if data.get("data"):
                    data = data[
                        "data"
                    ]  # this will eliminate any data passed as title="thing"
            # Added check for XML, because we don't want to mess with XML
            if headers.get("Content-Type") != "application/xml" and data:
                # if not headers:  # This should never happen, because there is code above to set headers if they are missing - Turn this off at some point?
                #     data = json.dumps(data, cls=DecimalEncoder)
                #     headers = {'Content-Type': 'application/json'}
                if (
                    headers and "Content-Type" not in headers
                ):  # TODO: This is a hack to get around the fact that the headers are not being set properly
                    # External databases use decimals, but JSON doesn't support them. Convert to string if you find them
                    data = json.dumps(data, cls=DecimalEncoder)
                    headers["Content-Type"] = "application/json; charset=utf-8"
                else:
                    # Once headers have content type, we still need the right data
                    data = json.dumps(data, cls=DecimalEncoder)
            logger.debug(
                f"RUN METHOD: {method} {url}\nDATA:{data}\nHEADERS:{headers}\nFILES:{files}"
            )
            # make and send the request, refreshing the token if needed
            try:
                result = self._session.request(
                    method,
                    url,
                    data=data,
                    timeout=self.timeout,
                    headers=headers,
                    params=params,
                )
                # A 401 means the SERVER rejected this access token — ground truth that overrides
                # our local expiry clock. The old code only reset self.expires and called
                # _manage_token_refresh(), but atomic_refresh() gates on the *stored* token's clock
                # and would short-circuit (no real refresh) when a token was revoked BEFORE its
                # nominal expiry (refresh-token rotation). The reused dead token then 401'd again.
                # Now we FORCE a real refresh and pass the token that failed, so the store can adopt
                # a peer's newer token if present, else mint a fresh one regardless of the clock.
                if result.status_code == 401:
                    failed_token = getattr(self, "access_token", None)
                    if hasattr(self, "expires"):
                        self.expires = 0.0
                    self._manage_token_refresh(force=True, stale_access_token=failed_token)
                    result = self._session.request(
                        method,
                        url,
                        data=data,
                        timeout=self.timeout,
                        headers=headers,
                        params=params,
                    )
                    if result.status_code == 401:
                        # The forced refresh did NOT clear the 401. This should not happen once the
                        # force path works; if it does, the self-heal has regressed — be LOUD so it
                        # can't be missed (this also raises below via the status_code check).
                        broke_msg = (
                            "pyLightspeed SELF-HEAL FAILED — forced token refresh did not clear a "
                            f"401 @ {url}. Either the refresh token is genuinely revoked (re-run the "
                            "OAuth flow), or atomic_refresh(force=...) regressed. "
                            ">>> I AM STILL BROKE! HERE I AM! FIX ME! <<<"
                        )
                        logger.error(broke_msg)
                        print(f"\n*** {broke_msg} ***\n", flush=True)
                elif result.status_code == 429:
                    # Use the Retry-After header Lightspeed sends; fall back to
                    # 5s for burst limiter (needs ≥1s) or 30s for leaky bucket.
                    result = self._retry_after_429(result, method, url, data, headers, params)

                if result.status_code not in [200, 201]:
                    raise requests.exceptions.RequestException(
                        f"ERROR: {result.status_code} {result.reason} @ {url}: {result.content}"
                    )

                return result
            except requests.exceptions.RequestException as e:
                logger.error(f"ERROR: {e}")
                raise e

    # CRUD methods

    def get(self, resource="", rid=None, **query):
        """
        Retrieves the resource with given id 'rid', or all resources of given type.
        Keep in mind that the API returns a list for any query that doesn't specify an ID, even when applying
        a limit=1 filter.
        Also be aware that float values tend to come back as strings ("2.0000" instead of 2.0)
        Keyword arguments can be parsed for filtering the query, for example:
            connection.get('products', limit=3, min_price=10.5)
        (see Lightspeed resource API documentation).
        """
        if rid:
            if resource[-1] != "/":
                resource += "/"
            resource += str(rid)
        response = self._run_method("GET", resource, query=query)
        return self._handle_response(resource, response)

    def update(self, resource, rid, updates):
        """
        Updates the resource with id 'rid' with the given updates dictionary.
        """
        if resource[-1] != "/":
            resource += "/"
        resource += str(rid)
        return self.put(resource, data=updates)

    def create(self, resource, data):
        """
        Create a resource with given data dictionary.
        """
        return self.post(resource, data)

    def delete(self, resource, rid=None):  # note that rid can't be 0 - problem?
        """
        Deletes the resource with given id 'rid', or all resources of given type if rid is not supplied.
        """
        if rid:
            if resource[-1] != "/":
                resource += "/"
            resource += str(rid)
        response = self._run_method("DELETE", resource)
        return self._handle_response(resource, response, suppress_empty=True)

    # Raw-er stuff

    def make_request(
        self, method, url, data=None, params=None, headers=None, files=None
    ):
        self._manage_token_refresh()
        response = self._run_method(method, url, data, params, headers, files)
        return self._handle_response(url, response)

    def put(self, url, data):
        """
        Make a PUT request to save data.
        data should be a dictionary.
        """
        response = self._run_method("PUT", url, data=data)
        logger.debug("OUTPUT: %s" % response.content)
        return self._handle_response(url, response)

    def post(self, url: str, data, headers: dict = {}, files: dict | None = None):
        """POST request for creating new objects.

        Args:
            url (str): The endpoint URL.
            data (dict | str): Typically a dictionary. If uploading a file, may
                be a JSON string such as
                ``'{"description": "My Image", "itemID": "123"}'``.
            headers (dict): Override the default headers if needed.
            files: A requests file object, e.g.
                ``{'image': (filename, file, 'image/jpeg')}``.
        """
        response = self._run_method(
            "POST", url, data=data, files=files, headers=headers
        )
        logger.debug(f"POST:Data: {data} \n Headers: {headers} \n Response: {response}")
        return self._handle_response(url, response)

    def _retry_after_429(self, result, method, url, data, headers, params, max_retries: int = 3):
        """Retry a request that received a 429 Too Many Requests response.

        Uses the ``Retry-After`` header Lightspeed sends with every 429 to
        determine exactly how long to wait.  Distinguishes the two Lightspeed
        rate limiters:

        * ``api-burst-limiter`` — 1-second window; ``Retry-After`` is typically
          1-2 s.
        * ``api-leaky-bucket`` — bucket exhausted; ``Retry-After`` may be
          several seconds to minutes.

        Retries up to *max_retries* times.  If all retries return 429, the
        final response is returned and the caller raises an appropriate error.
        """
        for attempt in range(max_retries):
            limiter_type = result.headers.get("X-LS-API-RateLimit-Type", "api-leaky-bucket")
            retry_after = float(result.headers.get("Retry-After", 1 if "burst" in limiter_type else 30))
            logger.warning(
                f"429 {limiter_type} (attempt {attempt + 1}/{max_retries}) — "
                f"waiting {retry_after:.1f}s before retry: {url}"
            )
            sleep(retry_after)
            result = self._session.request(
                method, url, data=data, timeout=self.timeout,
                headers=headers, params=params,
            )
            if result.status_code != 429:
                break
        return result

    def _manage_token_refresh(self, force: bool = False, stale_access_token: str | None = None):
        """Monitors token refresh requirements where needed and refreshes the token if needed. This should be overridden by subclasses to handle the specific API type.

        force: when True (set by the 401 handler in :meth:`request`/run-method), bypass any
            "still valid by clock" short-circuit and obtain a genuinely fresh token. Auth
            subclasses MUST honour this or 401s caused by early-revoked tokens won't self-heal.
        stale_access_token: the access token that just 401'd, so the refresh can detect whether a
            peer already replaced it (and adopt that) instead of rotating the refresh token again.
        """
        return

    def _handle_result(self, res):
        """A helper method to parse the response and return the raw result as json or raise an exception. The result should always be an iterable object, even if it is empty."""
        # This should be overridden by subclasses to handle the specific API type. This actual function probably doesn't work well.
        try:
            result = res.json()
            # attaches the raw json to the result
            return result
        except Exception as e:  # json might be invalid, or store might be down
            e.__doc__ = (e.__doc__ or "") + (
                " (_handle_response failed to decode JSON: " + str(res.content) + ")"
            )
            raise

    def _handle_ratelimits(self, res):
        """Update the rate limit information after a request is made. This should be overridden by subclasses to handle the specific API type."""
        return

    def _handle_response(self, url, res, suppress_empty=True):
        """
        Returns parsed JSON or raises an exception appropriately.
        """
        self._last_response = res  # held for debugging
        result = {}
        if res.status_code in (200, 201, 202):
            self._handle_ratelimits(res)
            result = self._handle_result(res)
        elif res.status_code == 204 and not suppress_empty:
            raise EmptyResponseWarning(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        elif res.status_code >= 500:
            raise ServerException(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        elif res.status_code == 401:
            logger.warning(
                f"WARNING: TOKEN ERROR {res.status_code} {res.reason} @ {url}: {res.content}"
            )
            logger.debug(f"Headers are: {self._session.headers}")

            raise Unauthorised(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        elif res.status_code == 429:
            # If you get this, you need to fix the rate limit throttle
            raise RateLimitingException(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        elif res.status_code == 422:
            logger.warning(
                f"WARNING: UNPROCESSABLE ENTITY {res.status_code} {res.reason} @ {url}: {res.content}"
            )
            # return - May want to add some functionality to ignore errors here
            raise UnprocessableEntity(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        elif res.status_code >= 400:
            raise ClientRequestException(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        elif res.status_code >= 300:
            raise RedirectionException(
                "%d %s @ %s: %s" % (res.status_code, res.reason, url, res.content), res
            )
        return result

    def __repr__(self):
        return "%s %s%s" % (self.__class__.__name__, self.host, self.api_path)


class OAuthConnection(Connection):
    """Base class for Lightspeed OAuth connections.

    Manages OAuth token lifecycle: reading from a `TokenStore`, refreshing
    on expiry, and persisting updated tokens. Subclasses implement the actual
    token-refresh logic for their specific API series.

    Args:
        account_id: The Lightspeed account / store ID embedded in API paths.
        client_id (str): OAuth client ID from the Lightspeed developer dashboard.
        client_secret (str): OAuth client secret.
        token_file (str): Path to a JSON file holding the OAuth tokens. Ignored when
            *token_store* is provided. Defaults to ``"codes.json"``.
        host (str): API hostname.
        api_path (str): URL path template (must contain ``{}`` placeholders for
            account_id and resource).
        token_store (TokenStore | None): A `TokenStore` instance. When provided,
            *token_file* is ignored. When omitted, a `FileTokenStore` wrapping
            *token_file* is created automatically.
    """

    def __init__(
        self,
        account_id: str | None,
        client_id: str,
        client_secret: str,
        token_file: str = "codes.json",
        host: str = "api.lightspeedapp.com",
        api_path: str = "/API/Account/{}/{}",
        token_store: TokenStore | None = None,
    ):
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.host = host
        self.api_path = api_path

        # Token storage — prefer an explicit TokenStore; fall back to a file.
        if token_store is not None:
            self._token_store = token_store
        else:
            if token_file is None:
                token_file = "codes.json"
            self._token_store = FileTokenStore(token_file)

        # Expose token_file for backwards-compatible access and logging.
        self.token_file = getattr(self._token_store, "path", str(self._token_store))

        # Current OAuth endpoints (R-Series)
        self._token_refresh_url = "https://cloud.lightspeedapp.com/auth/oauth/token"
        self._authorization_base_url = "https://cloud.lightspeedapp.com/auth/oauth/authorize"

        self.response = None
        self.resource = ""
        self.request_counter = 0
        self.refresh_token = ""
        self.timeout = (10, 30)

        # Pagination state
        self.count = 0
        self.offset = 1
        self.limit = 100

        # Token state — populated by _manage_token_refresh()
        self.access_token = ""
        self.token_type = ""
        self.scope = ""
        self.expires_in = 0.0
        self.expires = 0.0

        self._session = requests.Session()
        self._session.headers = {
            "Accept": "application/json",
            "authorization": f"Bearer {self.access_token}",
        }

        logger.info(f"{self.__class__.__name__}: Creating connection (account={self.account_id})")

        self._last_response = None
        self.rate_limit = {}

        self._manage_token_refresh()

    def full_path(self, url):
        return "https://" + self.host + self.api_path.format(self.account_id, url)


class RSeriesConnection(OAuthConnection):
    """Connection for the Lightspeed Retail (R-Series) API using OAuth 2.0.

    On instantiation the token store is checked and the access token is refreshed
    if it has expired.  If no valid token is found a :class:`MissingTokenError` is
    raised — use :meth:`get_authorization_url` and :meth:`exchange_code_for_token`
    to perform the one-time OAuth setup (e.g. from a CLI script), then persist the
    result via your :class:`TokenStore`.
    """

    def __init__(
        self,
        account_id: str | None,
        client_id: str,
        client_secret: str,
        token_file: str = "codes.json",
        host: str = "api.lightspeedapp.com",
        api_path: str = "/API/Account/{}/{}",
        token_store: TokenStore | None = None,
    ):
        super().__init__(
            account_id, client_id, client_secret, token_file, host, api_path,
            token_store=token_store,
        )

    def _manage_token_refresh(self, force: bool = False, stale_access_token: str | None = None):
        """Refresh the R-Series access token when expired (or when *force* is set after a 401).

        Delegates to :meth:`~TokenStore.atomic_refresh` on the token store,
        which acquires an exclusive lock (file-based for all stores;
        additionally Vault CAS for :class:`VaultTokenStore`) before calling
        the OAuth API.  This guarantees that on a single machine only one
        process ever calls Lightspeed with a given ``refresh_token``,
        preventing the revocation race described in the Lightspeed docs.

        ``force`` (passed by the 401 handler in :class:`Connection`) bypasses the local-clock
        short-circuit so a server-rejected-but-clock-"valid" token is actually replaced. Without
        it, a token revoked before its nominal expiry (refresh-token rotation) would be reused and
        the retry would 401 again. ``stale_access_token`` lets the store adopt a peer's newer token
        instead of refreshing again.
        """
        if not force and time.time() < self.expires:
            logger.debug(
                f"{self}: Token still valid for {self.expires - time.time():.0f}s"
            )
            return

        logger.info(f"{self}: TOKEN REFRESH: acquiring lock… (force={force})")
        token_data, was_refreshed = self._token_store.atomic_refresh(
            self._fetch_refreshed_token,
            force=force,
            stale_access_token=stale_access_token,
        )
        if was_refreshed:
            logger.info(
                f"{self}: TOKEN REFRESH COMPLETE. "
                f"Expires in {token_data.get('expires_in')}s."
            )
        else:
            logger.info(
                f"{self}: TOKEN: loaded fresh token from store "
                "(another process already refreshed)."
            )
        self._apply_token(token_data)

    def _apply_token(self, token_data: dict) -> None:
        """Apply a token dict to this connection's session state."""
        self.access_token = token_data["access_token"]
        self.token_type = token_data.get("token_type", "Bearer")
        self.scope = token_data.get("scope", self.scope)
        self.expires_in = token_data.get("expires_in", 3600)
        self.expires = token_data.get("last_run", time.time()) + int(self.expires_in)
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        self._session.headers["authorization"] = f"Bearer {self.access_token}"

    def _fetch_refreshed_token(self, codes: dict) -> dict:
        """Exchange *codes["refresh_token"]* with Lightspeed for a new token pair.

        Called by :meth:`_manage_token_refresh` (directly or via
        :meth:`VaultTokenStore.atomic_refresh`).  Validates the *codes* dict,
        makes the Lightspeed OAuth token endpoint request, and returns the
        complete token dict ready to persist.

        Raises :class:`MissingTokenError` on missing / bad *codes*.
        """
        if codes is None:
            raise MissingTokenError(
                f"No token found in {self._token_store!r}. "
                "Run the OAuth setup flow."
            )
        if codes.get("error"):
            raise MissingTokenError(
                f"Token store contains an error entry: {codes['error']}. "
                "Delete the token file and re-authorise."
            )
        if "refresh_token" not in codes:
            raise MissingTokenError(
                f"Token data in {self._token_store!r} is missing 'refresh_token'. "
                "Re-run the OAuth setup flow."
            )

        payload = {
            "refresh_token": codes["refresh_token"],
            "client_secret": self.client_secret,
            "client_id": self.client_id,
            "grant_type": "refresh_token",
        }
        response = requests.post(self._token_refresh_url, data=payload)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            try:
                err_body = response.json()
            except Exception:
                err_body = {}
            error_code = err_body.get("error", "")
            if response.status_code == 400 and error_code == "invalid_grant":
                raise MissingTokenError(
                    f"R-Series refresh token is invalid or has been revoked "
                    f"(store: {self._token_store!r}). "
                    "The Retail POS user must re-authorize the application. "
                    "Call RSeriesConnection.get_authorization_url() to start the OAuth flow, "
                    "then RSeriesConnection.exchange_code_for_token() and save the result to "
                    "your token store."
                ) from exc
            raise

        new_codes = response.json()
        now = time.time()
        return {
            "access_token": new_codes["access_token"],
            "expires_in": new_codes.get("expires_in", 3600),
            "token_type": new_codes.get("token_type", "bearer"),
            "scope": new_codes.get("scope", codes.get("scope", self.scope)),
            # Lightspeed issues a new refresh_token on every refresh and
            # immediately revokes the old one — always persist the new one.
            "refresh_token": new_codes["refresh_token"],
            "last_run": now,
        }

    # ------------------------------------------------------------------
    # One-time OAuth setup helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_authorization_url(
        client_id: str,
        scope: str,
        redirect_uri: str,
        *,
        state: str | None = None,
        use_pkce: bool = True,
    ) -> tuple[str, str, str | None]:
        """Build the R-Series OAuth authorization URL.

        Intended to be called from an interactive setup script or a web-app
        callback handler — **not** from the connection constructor.

        Args:
            client_id (str): Your application's client ID.
            scope (str): Space-separated list of access scopes (e.g. ``"employee:all"``).
            redirect_uri (str): Must exactly match the redirect URI registered for
                your OAuth client.
            state (str | None): Optional CSRF-prevention token. A cryptographically
                random value is generated if not provided.
            use_pkce (bool): Generate a PKCE ``code_challenge`` (S256, strongly
                recommended). Defaults to ``True``.

        Returns:
            tuple[str, str, str | None]: A 3-tuple ``(url, state, code_verifier)``.
                *code_verifier* is ``None`` when *use_pkce* is ``False``; keep it
                to pass to `exchange_code_for_token`.
        """
        from urllib.parse import urlencode as _urlencode

        if state is None:
            state = secrets.token_urlsafe(24)

        params = {
            "response_type": "code",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
        }

        code_verifier: str | None = None
        if use_pkce:
            # RFC 7636 — code_verifier must be 43-128 base64url chars
            code_verifier = secrets.token_urlsafe(96)
            digest = hashlib.sha256(code_verifier.encode()).digest()
            code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        url = f"https://cloud.lightspeedapp.com/auth/oauth/authorize?{_urlencode(params)}"
        return url, state, code_verifier

    @staticmethod
    def exchange_code_for_token(
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        *,
        code_verifier: str | None = None,
    ) -> dict:
        """Exchange a temporary authorization code for access + refresh tokens.

        Call this once the user has approved the authorization request and your
        redirect URI has received the ``code`` parameter. Save the returned dict
        to a `TokenStore` so the connection can load and refresh it on future runs.

        Args:
            client_id (str): Your application's client ID.
            client_secret (str): Your application's client secret.
            code (str): The short-lived code from the OAuth callback (expires in 60 s).
            redirect_uri (str): The same redirect URI used in `get_authorization_url`.
            code_verifier (str | None): Required if PKCE was used in
                `get_authorization_url`.

        Returns:
            dict: Token dict with ``access_token``, ``refresh_token``,
                ``expires_in``, etc.

        Raises:
            requests.HTTPError: If the token endpoint returns an error.
        """
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if code_verifier is not None:
            payload["code_verifier"] = code_verifier

        response = requests.post(
            "https://cloud.lightspeedapp.com/auth/oauth/token", data=payload
        )
        response.raise_for_status()
        return response.json()

    def _handle_ratelimits(self, res):
        # Lightspeed R Series uses a leaky-bucket + burst rate limiter.
        # https://developers.lightspeedhq.com/retail/introduction/ratelimits/
        #
        # We apply two proactive slow-downs based on the response headers so
        # that we back off *before* receiving a 429, rather than only reacting
        # after one arrives.  When a 429 does arrive it is handled by
        # _retry_after_429 which uses the Retry-After header for precise waits.
        if "X-LS-API-Bucket-Level" in res.headers:
            api_drip_rate = float(res.headers.get("X-LS-Api-Drip-Rate", 1))
            api_bucket_level, api_bucket_size = [
                float(x) for x in res.headers["X-LS-API-Bucket-Level"].split("/")
            ]

            # --- Burst limiter proactive check ---
            # Lightspeed blocks at burst_size requests/second.  If we are above
            # 80 % of the burst window, pause for 1 s to let the window reset.
            if "X-LS-API-Burst-Level" in res.headers:
                burst_level, burst_size = [
                    float(x) for x in res.headers["X-LS-API-Burst-Level"].split("/")
                ]
                if burst_size > 0 and burst_level / burst_size >= 0.8:
                    logger.info(
                        f"{self}: burst level {burst_level:.0f}/{burst_size:.0f} — "
                        "pausing 1s to let burst window reset."
                    )
                    sleep(1)

            # --- Leaky-bucket proactive check ---
            # The largest individual request costs 10 drips.  Keep a headroom
            # of 10 so the next request is never immediately rate-limited.
            logger.debug(
                f"{self}: bucket {api_bucket_level:.1f}/{api_bucket_size:.1f} "
                f"drip-rate={api_drip_rate}/s"
            )
            headroom = api_bucket_size - api_bucket_level
            if headroom < 10:
                # Wait just long enough for the bucket to drain below the
                # headroom threshold at the current drip rate.
                wait = (10 - headroom) / max(api_drip_rate, 0.1)
                logger.info(
                    f"{self}: bucket headroom {headroom:.1f} < 10 — "
                    f"waiting {wait:.1f}s for bucket to drain."
                )
                sleep(wait)
        return

    def _handle_result(self, res) -> list:
        """Returns a dict or list based on the type of result from R-series API."""
        try:
            orig_result = res.json()

            # Lightspeed Retail API returns two top level results in the json - the @attributes which includes count, offset, and limit,
            # and a second block that actually has the thing from the API.
            # So let's hold the count, offset, and limit in the Connection object for use in other methods.

            # if the count is divisible by the limit, then there are more results to get, and lightspeed will return only count in attributes {"@attributes":{"count":"8300"}}
            # Normal GETs return a list with two keys - @attributes and the name of the object. For example:
            # {'@attributes': {'count': '1392', 'offset': '0', 'limit': '100'}, 'Item': [{'itemID':'1',...}, {...}, {...}, ...]}
            # GETs which return Zero items returns a result of {'@attributes': {'count': '0', 'offset': '0', 'limit': '100'}}
            # GETs with a single item usually return a result of '{"@attributes":{"count":"1"},"Vendor":{"vendorID":"1","name": but sometimes return a full {'@attributes': {'count': '1392', 'offset': '0', 'limit': '100'}... haven't figured out what causes the difference - could be Lightspeeds api, could be my handling

            # If the result is zero items, the API returns {'@attributes': {'count': '0'}}
            if int(orig_result["@attributes"]["count"]) == 0:
                self.offset = 0
                self.limit = 100
                self.count = 0
                result = []
            # If the result is a list of items, then we need to check the count, offset, and limit to see if there are more items to get.
            # GET include these, PUT don't. GETs that a return a single item have no offset or limit
            elif (
                "offset" in orig_result["@attributes"]
                and int(orig_result["@attributes"]["count"]) > 1
            ):
                if "offset" in orig_result["@attributes"]:
                    # + int(result['@attributes']['limit'])
                    self.offset = int(orig_result["@attributes"]["offset"])
                    self.limit = int(orig_result["@attributes"]["limit"])
                    self.count = int(orig_result["@attributes"]["count"])
                # This strips off whatever is the resulting object's name and return the dict so that Mapping can convert it to a resource object.
                # resource is something like Item/1234 (Endpoint name and ID), so get the Endpoint name which is the key in the response dict
                self.resource = list(orig_result.keys())[1]
                result = orig_result[self.resource]
                # Loop through the results and add the raw json to each item, which will be converted to a property later.
                # Snapshot BEFORE adding "json" to avoid a self-referential dict (the item and the source are the same object).
                for new_item in result:
                    new_item["json"] = {k: v for k, v in new_item.items()}

            # If the result is a single item, R-series returns {'@attributes': {'count': '1', 'offset': '0', 'limit': '100'} if it was a query with one result or just if it was a get by itemID {"@attributes":{"count":"1"}
            # Regardless, dealing with 1 item needs to be handled differently
            # GETs that return a single item have no offset or limi
            elif int(orig_result["@attributes"]["count"]) == 1:
                self.offset = 1
                self.count = 1
                self.limit = (
                    100  # Not sure this is needed, but it is a default value for limit
                )
                # This strips off whatever is the resulting object's name and return the dict so that Mapping can convert it to a resource object.
                # resource is something like Item/1234 (Endpoint name and ID), so get the Endpoint name which is the key in the response dict
                self.resource = list(orig_result.keys())[1]

                result = orig_result[self.resource]
                # Snapshot BEFORE adding "json" to avoid a self-referential dict.
                result["json"] = {k: v for k, v in result.items()}
                # If the original call was a .get() or .update() return the result as one dict (which will be converted later to an object), but if it was list(), or list_all() return a list of one dict (which will be converted to a list of one object)
                # If limit is in the attributes, then it was a list() or list_all() call which should return a list
                if "limit" in orig_result["@attributes"]:
                    result = [result]

            # Must have returned 0 items and GETs that return zero items have no offset or limit
            else:
                # try: # I just dumped some things in here, probably bad
                self.offset = int(orig_result["@attributes"]["offset"])
                self.limit = 100
                try:
                    self.count = int(orig_result["@attributes"]["count"])
                except:
                    self.count = 0
                # self.resource = "" Probably should just leave it what it was?
                self.json = {}  # Added so the properties are consistent, even if there is no data
                result = []
                # except:
                #     self.offset = self.count # so that it works when count is divisible by limi

            return result

        except Exception as e:  # json might be invalid, or store might be down
            # there is an issue that occurs then the number of items is divisible by 100 that throws an error. Rather than address it, just return the result and keep moving

            e.__doc__ += (
                " (_handle_result failed to decode JSON: " + str(res.content) + ")"
            )


class CSeriesConnection(Connection):
    def _handle_result(self, res):
        """Returns a list, dict, or raw response depending on the endpoint.

        Most C-Series endpoints wrap their payload under a resource key, e.g.
        ``{"brand": {...}}`` or ``{"brands": [...]}``.  This method strips that
        outer key and returns the inner value.

        *Scalar* responses such as the ``/count`` endpoint  (``{"count": 42}``)
        are returned as-is (the full dict) so that callers like
        ``CountableApiResource.count()`` can do ``response["count"]`` correctly.
        """
        orig_result = res.json()
        try:
            # Strip the outer resource key that C-Series wraps all payloads in.
            self.resource = list(orig_result.keys())[0]
            result = orig_result[self.resource]

            # Scalar value (e.g. count endpoint returns {"count": 42}).
            # Return the full dict so callers can access the key by name.
            if not isinstance(result, (dict, list)):
                return orig_result

            # Empty collection
            if len(result) == 0:
                self.json = {}
                return []

            # Single object returned as a dict
            if isinstance(result, dict):
                # Snapshot BEFORE adding "json" to avoid a self-referential dict.
                result["json"] = {k: v for k, v in result.items()}
            else:
                # List of objects — attach raw json snapshot to each item before adding the key.
                for new_item in result:
                    new_item["json"] = {k: v for k, v in new_item.items()}

            return result

        except Exception as e:  # json might be invalid, or store might be down
            e.__doc__ = (e.__doc__ or "") + (
                " (_handle_result failed to decode JSON: " + str(res.content) + ")"
            )
            raise


class XSeriesPersonalConnection(Connection):
    """
    Makes a connection to the Lightspeed X-Series API
    XSeries as several differences from the eCom API including:
        - Supports both a personal token and an Oauth token
        - Requires a different endpoint including version number
        - Only supports JSON
        - Has a different rate limiting algorithm which is used on both personal and Oauth tokens
        - Expects a different header including a User Agent

    """

    def __init__(self, host, auth, api_path="/api/{}/{}", format=""):
        self.host = host
        self.api_path = api_path  # API Path should be set in api.py
        self.api_version = "2.0"
        # Lightspeed will return json or xml depending on extension. For simplicity, defining it at the object not method.
        self.format = format

        self.response = None
        self.request_counter = 0
        self.resource = ""

        self.page_min = 0  # These are used for X pagination
        self.page_max = 0
        self.has_next = False
        self.last_seen = ""

        self.timeout = 7.0  # need to catch timeout?

        logger.info("API Host: %s/%s" % (self.host, self.api_path))

        # Set up the Session using requests library and let the Session hold the auth and headers. See: https://2.python-requests.org/projects/3/user/advanced/#session-objects
        self._session = requests.Session()
        self._session.auth = None

        # Leaving this in case header changes are needed later, but LSeCom needs no special header
        self._session.headers = {
            "User-Agent": f"pyLightspeed/{self.host}",
            "Accept": "application/json",
            "authorization": f"Bearer {auth}",
        }
        # Not sure why there is a second copy of the headers, but it is used in the make_request method
        # self.headers = {"User-Agent": f"pyLightspeed/{self.host}", "Accept": "application/json", "authorization": f"Bearer {auth}"}

        self._last_response = None  # for debugging

    def full_path(self, url):
        # X Series requires a version number in the path and no extension
        # i.e. https://domain_prefix.vendhq.com/api/2.0/products

        # if the url already has a version number (such as 2.1 or 3.0) that is different than the one in the api_path, don't add the api_path version number, just use the url as is
        # at the time of doing this, here seems to be the best place to catch exception that come in at the call level. Originally added because the X Product list endpoint is 2.0 and the update endpoint is 2.1
        if url.startswith(
            "api/"
        ):  # if we need to change the version, override the _whatever_path method in the resource class and start the url with api/X.X
            return "https://" + self.host + "/" + url
        else:
            return "https://" + self.host + self.api_path.format(self.api_version, url)

    def _handle_ratelimits(self, res):
        # https://docs.vendhq.com/docs/rate_limiting
        # Does the api sometimes not return the rate limit headers? I think so, but I can't find the documentation.
        if "x-ratelimit-limit" in res.headers:
            rate_limit = int(res.headers.get("X-RateLimit-Limit", 0))
            rate_remaining = int(res.headers.get("X-RateLimit-Remaining", 0))
            retry_after = int(res.headers.get("Retry-After", 0))
            logger.debug(f"Rate Limit: {rate_limit} Rate Remaining: {rate_remaining}")
            if rate_remaining == 0:
                logger.debug(f"Rate limit reached. Waiting for {retry_after} seconds...")
                time.sleep(retry_after)
        return

    def _handle_result(self, res):
        # X-Series returns json like {'includes': None, 'data': {'id': '7eb310ba-...
        # So pull out only the data key
        try:
            if "includes" in res.json():
                self.includes = res.json()["includes"]
            if "version" in res.json():
                self.page_min = res.json()["version"]["min"]
                self.page_max = res.json()["version"]["max"]
                if self.page_max:  # added this because sometimes need to check has_next to manage pagination of the product_categories endpoint (and maybe others). Having this False cause a problem with page and paginate on the resource
                    self.has_next = True
            if "data" in res.json():
                # When creating a new item, X-series returns the id in the data key as a string. We need to return it as a dict so it will be convted to an object
                if res.request.method == "POST":
                    result = {"id": res.json()["data"]}
                    result["json"] = res.json()
                # Otherwise if was probably a GET request and we can return the data key as is
                else:
                    result = res.json()["data"]
                    if (
                        "page_info" in result
                    ):  # This is showing up on the product_categories endpoint as data:{"page_info":..., "data":"categories":{}...}. Not sure if this is everywhere or just there.
                        self.has_next = result["page_info"]["has_next"]
                        self.last_seen = result["page_info"]["last_seen"]
                        self.page_max = result[
                            "page_info"
                        ][
                            "last_seen"
                        ]  # see the doc on the 200 response for the product_categories endpoint - works differently than the others
                        # Since the result is coming {"page_info":..., "data":"categories":{}...} we need to pull out the just the "categories" key
                        result = result[
                            "data"
                        ][
                            list(result["data"])[0]
                        ]  # the name is not the same as the end point, so going to hope it is always the first key
                    # On updates, X-Series returns the id in the data key as a string. We need to return it as a dict so it will be convted to an object
                    if isinstance(result, str):
                        result = {"id": res.json()["data"]}
                        result["json"] = res.json()["data"]
                        result = [result]  # always return a list

                    # If the result is a dict it is only one record, so attach the json to it. Id the result is a list, loop through and attach the json to each item
                    if isinstance(result, dict):
                        result["json"] = res.json()["data"]
                    else:
                        # Adds the json property
                        for new_item, source_item in zip(result, res.json()["data"]):
                            new_item["json"] = source_item

        except Exception as e:  # json might be invalid, or store might be down
            e.message += (
                " (_handle_response failed to decode JSON: " + str(res.content) + ")"
            )
            raise  # TODO better exception
        return result


class XSeriesOauthConnection(XSeriesPersonalConnection):
    """Connection for the Lightspeed Retail X-Series API using OAuth 2.0.

    Differs from :class:`XSeriesPersonalConnection` in that:

    * Credentials are stored and refreshed automatically via a :class:`TokenStore`.
    * The API host is derived from the ``domain_prefix`` embedded in the token
      (returned by the X-Series OAuth endpoint) so you don't need to supply it
      separately.
    * If no valid token is present a :class:`MissingTokenError` is raised — use
      :meth:`get_authorization_url` and :meth:`exchange_code_for_token` to perform
      the one-time setup, then persist the token dict via a :class:`TokenStore`.

    X-Series OAuth documentation:
    https://x-series-api.lightspeedhq.com/docs/authorization
    """

    _API_SERVICE = "retail.lightspeed.app"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_store: TokenStore,
        api_path: str = "/api/{}/{}",
        format: str = "",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token_store = token_store

        self.api_path = api_path
        self.api_version = "2.0"
        self.format = format

        self.response = None
        self.request_counter = 0
        self.resource = ""

        self.page_min = 0
        self.page_max = 0
        self.has_next = False
        self.last_seen = ""

        self.timeout = 7.0

        # Populated from token data by _manage_token_refresh()
        self.domain_prefix: str | None = None
        self.host: str | None = None
        self.access_token: str = ""
        self.expires: float = 0.0

        self._session = requests.Session()
        self._session.auth = None
        self._session.headers = {
            "Accept": "application/json",
        }
        self._last_response = None

        self._manage_token_refresh()

    # -- Path -------------------------------------------------------------------

    def full_path(self, url: str) -> str:
        if not self.host:
            raise MissingTokenError(
                "No host available. Call _manage_token_refresh() first."
            )
        if url.startswith("api/"):
            return "https://" + self.host + "/" + url
        return "https://" + self.host + self.api_path.format(self.api_version, url)

    # -- Token management -------------------------------------------------------

    def _token_endpoint(self) -> str:
        if not self.domain_prefix:
            raise MissingTokenError(
                "domain_prefix is not set. Token must be loaded before making requests."
            )
        return f"https://{self.domain_prefix}.{self._API_SERVICE}/api/1.0/token"

    def _manage_token_refresh(self, force: bool = False, stale_access_token: str | None = None) -> None:
        """Load token from store, refresh if expired (or when *force* is set after a 401), update session headers.

        X-Series uses an absolute ``expires`` Unix timestamp (not ``expires_in``).
        ``force`` (set by the 401 handler) bypasses the local-clock check so a server-rejected
        token is actually re-minted. ``stale_access_token`` is accepted for signature parity with
        the base / R-Series refresh (X-Series refreshes inline, so it is not otherwise used here).
        Raises :class:`MissingTokenError` when no valid token is available.
        """
        codes = self._token_store.load_token()

        if codes is None or "refresh_token" not in codes:
            raise MissingTokenError(
                f"No valid X-Series token found in {self._token_store!r}. "
                "Run the OAuth setup flow: call XSeriesOauthConnection.get_authorization_url() "
                "to generate the authorization URL, direct a retailer to it, then pass the "
                "returned code and domain_prefix to XSeriesOauthConnection.exchange_code_for_token() "
                "and save the result to your token store."
            )

        if codes.get("error"):
            raise MissingTokenError(
                f"Token store contains an error entry: {codes['error']}. "
                "Re-run the OAuth setup flow."
            )

        self.domain_prefix = codes.get("domain_prefix")
        self.host = f"{self.domain_prefix}.{self._API_SERVICE}"

        # X-Series returns the absolute expiry as `expires` (Unix timestamp).
        # Refresh if within 60 seconds of expiry.
        token_expires = float(codes.get("expires", 0))
        if not force and time.time() < token_expires - 60:
            self.access_token = codes["access_token"]
            self.expires = token_expires
            self._session.headers["User-Agent"] = f"pyLightspeed/{self.host}"
            self._session.headers["authorization"] = f"Bearer {self.access_token}"
            logger.debug(
                f"X-Series token still valid for {token_expires - time.time():.0f}s"
            )
            return

        logger.info(f"XSeriesOauthConnection({self.host}): TOKEN REFRESH…")
        payload = {
            "refresh_token": codes["refresh_token"],
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        response = requests.post(self._token_endpoint(), data=payload)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            try:
                err_body = response.json()
            except Exception:
                err_body = {}
            error_code = err_body.get("error", "")
            if response.status_code == 400 and error_code == "invalid_grant":
                raise MissingTokenError(
                    f"X-Series refresh token is invalid or has been revoked "
                    f"(store: {self._token_store!r}). "
                    "The Retail POS user must re-authorize the application. "
                    "Call XSeriesOauthConnection.get_authorization_url() to start the OAuth flow, "
                    "then XSeriesOauthConnection.exchange_code_for_token() and save the result to "
                    "your token store."
                ) from exc
            raise
        new_codes = response.json()

        # Update in-memory state
        self.domain_prefix = new_codes.get("domain_prefix", self.domain_prefix)
        self.host = f"{self.domain_prefix}.{self._API_SERVICE}"
        self.access_token = new_codes["access_token"]
        self.expires = float(new_codes["expires"])

        self._token_store.save_token(new_codes)
        self._session.headers["User-Agent"] = f"pyLightspeed/{self.host}"
        self._session.headers["authorization"] = f"Bearer {self.access_token}"
        logger.info(f"XSeriesOauthConnection({self.host}): TOKEN REFRESH COMPLETE.")

    # -- One-time OAuth setup helpers -------------------------------------------

    @staticmethod
    def get_authorization_url(
        client_id: str,
        scope: str,
        redirect_uri: str,
        state: str,
    ) -> str:
        """Build the X-Series OAuth authorization URL.

        Redirect or link a retailer to this URL so they can authorize your
        application. Once approved, Lightspeed will redirect to *redirect_uri*
        with ``code``, ``domain_prefix``, ``state``, and ``scope`` query params.

        Args:
            client_id (str): Your application's client ID.
            scope (str): Space-separated list of access scopes.
            redirect_uri (str): Must match the redirect URI registered for your
                OAuth client.
            state (str): Required CSRF token — must be at least 8 characters.
                Generate one per request with e.g. ``secrets.token_urlsafe(12)``.

        Returns:
            str: The full authorization URL string.
        """
        from urllib.parse import urlencode as _urlencode

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope,
        }
        return f"https://secure.retail.lightspeed.app/connect?{_urlencode(params)}"

    @staticmethod
    def exchange_code_for_token(
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        domain_prefix: str,
    ) -> dict:
        """Exchange a temporary authorization code for OAuth tokens.

        Call this once you receive the ``code`` and ``domain_prefix`` at your
        redirect URI. Save the returned dict to a `TokenStore`.

        Args:
            client_id (str): Your application's client ID.
            client_secret (str): Your application's client secret.
            code (str): The short-lived authorization code from the OAuth callback.
            redirect_uri (str): The same redirect URI used in `get_authorization_url`.
            domain_prefix (str): The retailer's domain prefix as returned in the
                OAuth callback (e.g. ``"mystore"`` for
                ``mystore.retail.lightspeed.app``).

        Returns:
            dict: Token dict containing ``access_token``, ``refresh_token``,
                ``expires`` (absolute Unix timestamp), ``expires_in``,
                ``domain_prefix``, and ``scope``.

        Raises:
            requests.HTTPError: If the token endpoint returns an error.
        """
        token_url = (
            f"https://{domain_prefix}.retail.lightspeed.app/api/1.0/token"
        )
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        return response.json()




class ESeriesConnection(Connection):
    """Connections to the E-Series (Ecwid) API"""

    # If a property is empty, the endpoint doesn't return the property. so not "thing": None, just doesn't return thing

    def __init__(self, store_id, host, auth, api_path="/api/{}/{}", format=""):
        self.host = host
        # Ecwid api path is https://app.ecwid.com/api/v3/{storeId}/{endpoint}/{endpointtId}
        self.api_version = "v3"
        self.api_path = (
            api_path.format(self.api_version, store_id) + "/{}"
        )  # API Path should be set in api.py

        # Lightspeed will return json or xml depending on extension. For simplicity, defining it at the object not method.
        self.format = format

        self.response = None
        self.request_counter = 0
        self.resource = ""

        self.page_min = 0  # These are used for X pagination
        self.page_max = 0
        self.has_next = False
        self.last_seen = ""
        # Add these to handle pagination
        self.count = 0
        self.offset = 1
        self.limit = 100

        self.timeout = 12.0  # need to catch timeout?

        logger.info("API Host: %s/%s" % (self.host, self.api_path))

        # Set up the Session using requests library and let the Session hold the auth and headers. See: https://2.python-requests.org/projects/3/user/advanced/#session-objects
        self._session = requests.Session()
        self._session.auth = None

        # Leaving this in case header changes are needed later, but LSeCom needs no special header
        self._session.headers = {
            "accept": "application/json",
        }
        self._session.params = {
            "token": auth
        }  # E Series passes the token as part of the parameters not in the header if you are using the single store token instead oauth
        # Not sure why there is a second copy of the headers, but it is used in the make_request method
        # self.headers = {"User-Agent": f"pyLightspeed/{self.host}", "Accept": "application/json", "authorization": f"Bearer {auth}"}

        self._last_response = None  # for debugging

    def full_path(self, url):
        return "https://" + self.host + self.api_path.format(url) + self.format

    def _handle_result(self, res) -> list:
        """Returns a list of dicts, and None if there is no result."""

        orig_result = res.json()
        try:
            # One item comes back as a dict. Pages of items come back as a dict with pagination data and the "items" key with a list of items
            if orig_result.get("items") is None:
                orig_result["json"] = orig_result
                result = orig_result
                self.has_next = False
                self.offset = 0
                self.limit = 1
                self.count = 1
            # Otherwise it is a list of items, so process the list which includes data about the number of records
            # {"total":1524,"count":100,"offset":0,"limit":100,"items":[{"id":645582361,
            else:
                self.offset = int(orig_result["offset"])
                self.limit = int(orig_result["limit"])
                self.count = int(orig_result["total"])
                self.has_next = (
                    True if self.count >= (self.offset + self.limit) else False
                )
                result = orig_result[
                    "items"
                ]  # I assume items is consisten and not related to the endpoint. We shall see.

                # Loop through the results and add the raw json to each item, which will be converted to a property later

                for new_item, source_item in zip(result, orig_result["items"]):
                    new_item["json"] = source_item

            # per our new standard, if there is no result return an empty list
            if len(result) == 0:
                self.json = {}
                result = []

            return result

        except Exception as e:  # json might be invalid, or store might be down
            e.__doc__ += (
                " (_handle_response failed to decode JSON: " + str(res.content) + ")"
            )
