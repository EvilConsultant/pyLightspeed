"""
This module contains the implementation of the Lightspeed API client.

The LightspeedApi class is the base class for interacting with the Lightspeed API. It provides methods for authentication and making API requests.

The LightspeedCSeriesApi class is a subclass of LightspeedApi and is used for interacting with the Lightspeed eCom API, which uses basic authentication.

The LightspeedRSeriesApi class is a subclass of LightspeedApi and is used for interacting with the Lightspeed Retail API.

The LightspeedXSeriesApi class is a subclass of LightspeedApi and is used for interacting with the Lightspeed Retail X-Series API.

The LightspeedESeriesApi class is a subclass of LightspeedApi and is used for interacting with the Lightspeed eCom API, which uses basic authentication.

The module also contains helper classes and methods for handling API connections and authentication.

Classes:
- LightspeedApi: The base class for interacting with the Lightspeed API.
- LightspeedCSeriesApi: A subclass of LightspeedApi for interacting with the Lightspeed eCom API.
- LightspeedRSeriesApi: A subclass of LightspeedApi for interacting with the Lightspeed Retail API.
- LightspeedXSeriesApi: A subclass of LightspeedApi for interacting with the Lightspeed Retail X-Series API.
- LightspeedESeriesApi: A subclass of LightspeedApi for interacting with the Lightspeed eCom API.

Helper Classes:
- LightspeedApi.BatchJob: A class for managing batch jobs in the Lightspeed ESeries API.

Helper Methods:
- LightspeedApi.oauth_verify_payload: Verifies the payload using OAuth.
- LightspeedApi.oauth_verify_payload_jwt: Verifies the payload using OAuth JWT.

"""

import sys
from loguru import logger
from .connection import *
from .resources import *  # Needed for ApiResourceWrapper dynamic loading

logger = logger.bind(module="pylightspeed.api")

class LightspeedApi(object):
    """Base class for interacting with the Lightspeed API.

    In practice you should use one of the concrete subclasses
    (:class:`LightspeedRSeriesApi`, :class:`LightspeedCSeriesApi`, etc.) rather
    than instantiating this class directly.
    """

    def __getattr__(self, item):
        return ApiResourceWrapper(item, self)


class LightspeedCSeriesApi(LightspeedApi):
    """API client for the Lightspeed C-Series (eCom) API.

    Uses HTTP Basic Auth (API key + secret). No OAuth or token management required.
    """

    def __init__(self, host="api.shoplightspeed.com", api_key=None, api_secret=None, basic_auth=None, api_path="/us/{}"):
        """Initializes the LightspeedCSeriesApi instance.

        Args:
            host (str): The host of the API. Defaults to ``"api.shoplightspeed.com"``.
            api_key (str | None): The API key. Provide together with *api_secret* as an
                alternative to *basic_auth*.
            api_secret (str | None): The API secret.
            basic_auth (tuple | None): Pre-built ``(key, secret)`` tuple. Takes precedence
                over *api_key* / *api_secret* if both are supplied.
            api_path (str): The URL path template containing ``{}`` as the resource
                placeholder. Defaults to ``"/us/{}"``.
        """
        self.namespace = "CSeries"
        # you can either pass the api_key and api_secret or basic_auth. However, basic_auth is what is used.
        if api_key and api_secret:
            basic_auth = (api_key, api_secret)

        if host and basic_auth:
            self.connection = CSeriesConnection(host, basic_auth, api_path=api_path)
            self.created_at = "createdAt"
            self.updated_at = "updatedAt"


class LightspeedRSeriesApi(LightspeedApi):
    """API client for the Lightspeed R-Series (Retail) API.

    Uses OAuth 2.0 Authorization Code Grant with automatic token refresh.
    """

    def __init__(self, host="api.shoplightspeed.com", account_id=None, client_id=None, client_secret=None, token_file=None, token_store=None):
        """Initializes the LightspeedRSeriesApi instance.

        Args:
            host (str): Unused; kept for API compatibility.
            account_id (str | None): The Lightspeed account / store ID.
            client_id (str | None): OAuth client ID.
            client_secret (str | None): OAuth client secret.
            token_file (str | None): Path to the token JSON file. Ignored when
                *token_store* is provided. A `FileTokenStore` is created automatically
                from this path.
            token_store (TokenStore | None): A `TokenStore` instance for custom token
                persistence.
        """
        self.namespace = "RSeries"
        self.api_service = "api.lightspeedapp.com"
        self.auth_service = "cloud.lightspeedapp.com"
        if token_store is None and token_file:
            token_store = FileTokenStore(token_file)
        if client_id and client_secret and token_store:
            self.connection = RSeriesConnection(
                account_id, client_id, client_secret,
                host=self.api_service, token_store=token_store,
            )
            self.created_at = "createTime"
            self.updated_at = "timeStamp"


class LightspeedXSeriesApi(LightspeedApi):
    """API client for the Lightspeed X-Series (Retail X) API.

    Supports either a Personal Access Token (Plus-plan retailers) or full
    OAuth 2.0 credentials. See the
    [Connections guide](../connection.md#x-series-lightspeed-retail-x) for setup details.

    X-Series API reference: <https://x-series-api.lightspeedhq.com/reference>
    """

    def __init__(self, domain_prefix=None, personal_token=None, client_id=None, client_secret=None, token_file=None, token_store=None):
        """Initialize the X-Series API using either a Personal Access Token or OAuth credentials.

        Args:
            domain_prefix (str | None): The retailer's domain prefix (e.g.
                ``"mystore"`` for ``mystore.retail.lightspeed.app``). Required for
                personal-token connections; not needed for OAuth connections because
                the domain is embedded in the stored token.
            personal_token (str | None): A Personal Access Token (Plus plan retailers
                only).
            client_id (str | None): OAuth client ID.
            client_secret (str | None): OAuth client secret.
            token_file (str | None): Path to a token JSON file. Ignored when
                *token_store* is provided. A `FileTokenStore` is created automatically.
            token_store (TokenStore | None): A `TokenStore` instance for OAuth token
                storage.

        Raises:
            ValueError: If neither a personal-token pair nor OAuth credentials are
                provided.
        """

        self.namespace = "XSeries"
        self.created_at = "created_at"
        self.updated_at = "updated_at"
        self.api_service = "retail.lightspeed.app"
        self.auth_service = "secure.retail.lightspeed.app"

        # Personal token connection
        if domain_prefix and personal_token:
            self.connection = XSeriesPersonalConnection(
                f"{domain_prefix}.{self.api_service}", personal_token, format=""
            )

        # OAuth connection
        elif client_id:
            if token_store is None and token_file:
                token_store = FileTokenStore(token_file)
            if token_store is None:
                raise ValueError(
                    "An OAuth connection requires either token_store or token_file."
                )
            self.connection = XSeriesOauthConnection(
                client_id,
                client_secret,
                token_store,
            )

        else:
            raise ValueError(
                "Provide domain_prefix + personal_token for a personal-token connection, "
                "or client_id + (token_file or token_store) for an OAuth connection."
            )


class LightspeedESeriesApi(LightspeedApi):
    """API client for the Lightspeed E-Series (Ecwid) API.

    Passes the API secret as a query parameter on every request.

    Args:
        store_id (str): The Ecwid store ID.
        host (str): The host URL for the API. Defaults to ``"app.ecwid.com"``.
        api_public (str | None): The store's public token (read-only access).
            Either *api_public* or *api_secret* must be provided.
        api_secret (str | None): The secret API key. Either *api_public* or
            *api_secret* must be provided.

    Raises:
        Exception: If neither *api_public* nor *api_secret* are provided.
    """

    class BatchJob(object):
        def __init__(self, parent, name, stop_on_first_failure=True, allow_parallel_mode=False):

            self.parent = parent
            self.name = name
            self.body = []
            self.body_history = []
            self.count = 0
            self.total_count = 0
            self.stop_on_first_failure = stop_on_first_failure
            self.allow_parallel_mode = allow_parallel_mode
            self.ticket = None

        def build_batch_body(self, id: int, path: str, method: str, body: dict) -> dict:
            """
            Builds the correct data structure for a call to the batch endpoint.

            Args:
                id (int): The ID of the request.
                path (str): The path of the request.
                method (str): The HTTP method of the request.
                body (dict): The body of the request.

            Returns:
                dict: The data structure for the batch request.

            Example:
                {
                    "id": 645582630,
                    "path": "/products/645582630",
                    "method": "PUT",
                    "body": {"categoryIds": [167852527, 166927253, 167852536], "subtitle": "Changed by batch 1"}
                }
            """
            return {"id": id, "path": path, "method": method, "body": body}

        def batch_add(self, data=None):
            """
            Adds a request to the batch by appending it to self.body and incrementing count.
            """
            self.body.append(data)
            self.count += 1
            return self.batch_manager()

        def batch_manager(self, process=False):
            """
            Manages the batch by monitoring the count and issuing a create request when the count reaches 100 if allowParallelMode is true or 500 if false.
            Pass process=True to process the batch immediately.
            """
            if process or (self.count == 100 and self.allow_parallel_mode == True) or (self.count == 500 and self.allow_parallel_mode == False):
                result = self.parent.Batch.create(
                    params={"stopOnFirstFailure": self.stop_on_first_failure, "allowParallelMode": self.allow_parallel_mode}, data=self.body
                )
                logger.debug(f"Batch {self.name} processed with {self.count} items")
                self.body_history.append(self.body)
                self.body = []
                self.total_count += self.count
                self.count = 0
                # if the result includes a ticket, store it for later use
                if "ticket" in result:
                    self.ticket = result["ticket"]
            else:
                result = {"count": self.count, "stopOnFirstFailure": self.stop_on_first_failure, "allowParallelMode": self.allow_parallel_mode}
            return result

        def batch_execute(self, delete=False):
            """
            Executes the batch, optionally deleting it after execution.
            """
            result = self.batch_manager(process=True)
            if delete:
                self.batch_delete()
            return result

        def batch_delete(self):
            """
            Deletes the batch from the LightspeedESeriesApi instance.
            """
            self.parent.batches.pop(self.name)

        def batch_status(self):
            """
            Checks the status of the batch.
            """
            if self.ticket:
                return self.parent.Batch.page(ticket=self.ticket)
            else:
                return None

    def __init__(self, store_id, host="app.ecwid.com", api_public=None, api_secret=None):
        self.namespace = "ESeries"
        self.created_at = "createdAt"
        self.updated_at = "updatedAt"
        self.host = host
        if api_secret:
            auth = api_secret
        elif api_public:
            auth = api_public
        else:
            raise Exception("Must provide host, api_key, and api_secret for Lightspeed ESeries connection")

        self.connection = ESeriesConnection(store_id, host, auth)

        self.batches = {}

    def create_batch(self, name):
        self.batches[name] = self.BatchJob(self, name)
        return self.batches[name]


class ApiResourceWrapper(object):
    """
    Provides dot access to each of the API resources
    while proxying the connection parameter so that
    the user does not need to know it exists
    """

    def __init__(self, resource_class: "str | type", api: "LightspeedApi"):
        """Create a new resource wrapper.

        Args:
            resource_class (str | type): String name or class to proxy.
            api: The API instance whose connection should be used.
        """
        if isinstance(resource_class, str):
            self.resource_class = self.str_to_class(api.namespace, resource_class)
        else:
            self.resource_class = resource_class
        self.connection = api.connection

    def __getattr__(self, item):
        """
        Proxies access to all methods on the resource class,
        injecting the connection parameter before any
        other arguments
        """

        return lambda *args, **kwargs: (getattr(self.resource_class, item))(*args, connection=self.connection, **kwargs)

    @classmethod
    def str_to_class(cls, namespace, str):
        """
        Transforms a string class name into a class object
        Assumes that the class is already loaded.
        Appends the namespace to the class name so the user does not need to know it exists or use it in the call
        """
        return getattr(sys.modules[__name__], namespace + str)
