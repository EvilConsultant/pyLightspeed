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

import logging

import sys
from .connection import *
from .resources import *  # Needed for ApiResourceWrapper dynamic loading

_logger_name = "BA.pylightspeed.api"
logger = logging.getLogger(_logger_name)

class LightspeedApi(object):
    """
    The base class for interacting with the Lightspeed API.

    .. automethod:: oauth_verify_payload
    .. automethod:: oauth_verify_payload_jwt
    """

    def __init__(
        self,
        namespace,
        host="api.shoplightspeed.com",
        api_key=None,
        api_secret=None,
        basic_auth=None,
        account_id=None,
        client_id=None,
        client_secret=None,
        token_file=None,
    ):
        self.api_service = "api.lightspeedapp.com"  # os.getenv('BC_API_ENDPOINT', 'api.shoplightspeed.com/en/')
        self.auth_service = "cloud.lightspeedapp.com"  # os.getenv('BC_AUTH_SERVICE', 'api.shoplightspeed.com/en/')
        self.namespace = namespace
        # you can either pass the api_key and api_secret or basic_auth. However, basic_auth is what is used.
        if api_key and api_secret:
            basic_auth = (api_key, api_secret)

        # Leaving this in for backwards compatibility
        # Namespace is determines which API is used
        # This is for Lightspeed eCom, which uses basic auth
        if namespace == "CSeries" and host and basic_auth:
            self.connection = Connection(host, basic_auth)
            self.created_at = "createdAt"
            self.updated_at = "updatedAt"
        # This is for Lightspeed Retail, which uses OAuth
        elif namespace == "RSeries" and client_id and token_file:
            self.connection = OAuthConnection(
                account_id,
                client_id,
                client_secret,
                token_file,
                self.api_service,
            )
            self.created_at = "createTime"
            self.updated_at = "timeStamp"
        # For X-Series, call it directly...just left this in for backwards compatibility
        else:
            raise Exception(
                "Must provide host, api_key, and api_secret for Lightspeed eCom connection or client_id and token_file for Lightspeed Retail connection"
            )

    def oauth_fetch_token(self, client_secret, code, context, scope, redirect_uri):
        if isinstance(self.connection, OAuthConnection):
            token_url = "https://%s/oauth2/token" % self.auth_service
            return self.connection.fetch_token(client_secret, code, context, scope, redirect_uri, token_url)

    @classmethod
    def oauth_verify_payload(cls, signed_payload, client_secret):
        """
        Verifies the payload using OAuth. Doesn't work.

        :param signed_payload: The signed payload to verify.
        :type signed_payload: str
        :param client_secret: The client secret to use for verification.
        :type client_secret: str
        :return: The verification result.
        :rtype: bool
        """
        return OAuthConnection.verify_payload(signed_payload, client_secret)

    @classmethod
    def oauth_verify_payload_jwt(cls, signed_payload, client_secret, client_id):
        """
        Verifies the payload using OAuth JWT. Doesn't work.

        :param signed_payload: The signed payload to verify.
        :type signed_payload: str
        :param client_secret: The client secret to use for verification.
        :type client_secret: str
        :param client_id: The client ID to use for verification.
        :type client_id: str
        :return: The verification result.
        :rtype: bool
        """
        return OAuthConnection.verify_payload_jwt(signed_payload, client_secret, client_id)

    def __getattr__(self, item):
        return ApiResourceWrapper(item, self)


class LightspeedCSeriesApi(LightspeedApi):
    """
    This class is for the Lightspeed eCom API, which uses basic auth.

    .. automethod:: __init__
    """

    def __init__(self, host="api.shoplightspeed.com", api_key=None, api_secret=None, basic_auth=None, api_path="/us/{}"):
        """
        Initializes the LightspeedCSeriesApi instance.

        :param host: The host of the API.
        :type host: str
        :param api_key: The API key.
        :type api_key: str
        :param api_secret: The API secret.
        :type api_secret: str
        :param basic_auth: The basic auth credentials.
        :type basic_auth: tuple
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
    """
    This class is for the Lightspeed Retail API.

    .. automethod:: __init__
    """

    def __init__(self, host="api.shoplightspeed.com", account_id=None, client_id=None, client_secret=None, token_file=None):
        """
        Initializes the LightspeedRSeriesApi instance.

        :param host: The host of the API.
        :type host: str
        :param account_id: The account ID.
        :type account_id: str
        :param client_id: The client ID.
        :type client_id: str
        :param client_secret: The client secret.
        :type client_secret: str
        :param token_file: The token file.
        :type token_file: str
        """
        self.namespace = "RSeries"
        self.api_service = "api.lightspeedapp.com"
        self.auth_service = "cloud.lightspeedapp.com"
        if client_id and client_secret and token_file:
            self.connection = RSeriesConnection(account_id, client_id, client_secret, token_file, self.api_service)
            self.created_at = "createTime"
            self.updated_at = "timeStamp"


class LightspeedXSeriesApi(LightspeedApi):
    """
    This is the class for the Lightspeed Retail X-Series API. You can find documentation for the X-Series API at https://x-series-api.lightspeedhq.com/reference
    X gives you the option of using either a Personal Access Token or OAuth credentials. This implementation uses the Personal Access Token
    """

    def __init__(self, domain_prefix, personal_token=None, client_id=None, client_secret=None, access_token=None, refresh_token=None, token_file=None):
        """Initialize the X-Series API using either a Personal Access Token or OAuth credentials
        :param domain_prefix: the retailer prefix of the api url (e.g. "DOMAIN_PREFIX.vendhq.com")
        :param personal_token: a Personal Access Token for the retailer
        :param client_id: the OAuth client ID for the application (obtained from developer.vendhq.com)
        :param client_secret: the OAuth client secret for the application (obtained from developer.vendhq.com)
        :param access_token: the OAuth access token for the retailer
        :param refresh_token: the OAuth refresh token for the retailer
        :param token_file: the path to a file containing the OAuth tokens for the retailer
        """

        self.namespace = "XSeries"
        self.created_at = "created_at"
        self.updated_at = "updated_at"
        # https://docs.vendhq.com/docs/authorization
        self.api_service = "retail.lightspeed.app"
        self.auth_service = "secure.vendhq.com"

        # let's keep api_path in connection instead of API
        # self.api_path = "/api/{}/{}"  # XSeries API has different versions, so will need to inject them later

        # If you are using a personal token
        if domain_prefix and personal_token:
            # self.connection = XSeriesPersonalConnection(f"{domain_prefix}.{self.api_service}", personal_token, api_path=self.api_path, format="")
            self.connection = XSeriesPersonalConnection(f"{domain_prefix}.{self.api_service}", personal_token, format="")

        # if you are using OAuth
        elif client_id and token_file:
            self.connection = XSeriesOauthConnection(
                domain_prefix,
                client_id,
                client_secret,
                token_file,
                f"{domain_prefix}.{self.api_service}",
            )

        else:
            raise Exception(
                "Must provide host, api_key, and api_secret for Lightspeed eCom connection or client_id and token_file for Lightspeed Retail connection"
            )


class LightspeedESeriesApi(LightspeedApi):
    """
    This class is for the Lightspeed eCom API, which uses basic auth.

    :param store_id: The ID of the store.
    :param host: The host URL for the API. Default is "app.ecwid.com".
    :param api_public: The public API key for authentication. Either `api_public` or `api_secret` must be provided.
    :param api_secret: The secret API key for authentication. Either `api_public` or `api_secret` must be provided.
    :raises Exception: If `host`, `api_public`, and `api_secret` are not provided.

    .. automethod:: __init__
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

        def build_batch_body(self, id, path, method, body):
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

    def __init__(self, resource_class, api):
        """
        :param resource_class: String or Class to proxy
        :param api: API whose connection we want to use
        :return: A wrapper instance
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
