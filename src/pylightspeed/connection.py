"""
Connection Objects
=======
Connection handles the lower level stuff for the api such as making requests, handling responses, managing tokens, and rate limits.

The high level API provided by pylightspeed.api.LightspeedApi is a wrapper around a lower level api in pylightspeed.connection.
This can be accessed through api.connection, and provides helper methods for get/post/put/delete operation

Each series of Lightspeed API has a different way of handling authentication and rate limits, so the Connection class is subclassed for each series.
This also includes some standard methods including :py:func:`pylightspeed.connection._handle_response`, and :py:func:`pylightspeed.connection._handle_result` which are overridden by the subclasses.

.. note::

   While pagination is often specific to an API or connection, pyLightspeed keeps handling at the resource level to allow for more flexibility with resources/endpoints
   that have different pagination requirements based on version or other factors.

"""

from decimal import Decimal
import base64
import hashlib
import hmac

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


import requests

# import jwt

import json
import time
import os


from time import sleep

from .exception import *

# %% Logging Setup and Config
import logging

# Use the new centralized logging configuration.
_logger_name = "BA.pylightspeed.connection"
logger = logging.getLogger(_logger_name)

_env_level = os.getenv("PYLIGHTSPEED_LOG_LEVEL")
if _env_level:
    try:
        logger.setLevel(getattr(logging, _env_level.upper()))
    except AttributeError:
        logger.warning(
            "Invalid PYLIGHTSPEED_LOG_LEVEL '%s', using inherited level",
            _env_level,
            extra={"event": "config.warning"},
        )

logger.debug("Logger for connection.py initialized", extra={"event": "logger.init"})
# %%


# Handle Decimal types in JSON, see: https://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


class Connection(object):
    """
    Connection class manages the connection handles the basics of making requests, handling responses, CRUD operations, and rate limits.
    The majority of the Connection class is intended to be fairly universal.
    """

    def __init__(self, host, auth, api_path="", format="json"):
        """
        Initializes the connection with the host, auth, and api_path. This only handles very simple APIs = like Lightspeed C-Series
        The host is the base URL for the API, the auth is the authentication method (usually a tuple of username and password),
        and the api_path is the path to the API, which should include the version and store ID.
        The format is the format of the response, either 'json' or 'xml'.

        :param host: The base URL for the API.
        :type host: str
        :param auth: The authentication method for the API.
        :type auth: tuple
        :param api_path: The path to the API, including the version and store ID.
        :type api_path: str
        :param format: The format of the response, either 'json' or 'xml'.
        :type format: str

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

    def full_path(self, url):
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

        # This should attach the API authorization to the request if it is missing.
        # Removing this and adding the Auth check below because it fails to attach the auth if you pass in a header - for example a header setting the format to XML
        # if headers is None:
        #     headers = self.headers

        # if authorization is missing, add it by appending self.headers to headers dict
        # BUILDING HEADERS SUCKS AND NEEDS TO BE FIXED
        if headers is None:
            headers = self._session.headers
        # Check if authorization is needed and exists in headers, otherwise add it and only it - no other keys or headers
        if "authorization" not in headers and self._session.headers.get(
            "authorization"
        ):
            headers["authorization"] = self._session.headers.get("authorization")

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
                # if there is a 401 Unauthorized error, we need to refresh the token and try again
                if result.status_code == 401:
                    self._manage_token_refresh()
                    result = self._session.request(
                        method,
                        url,
                        data=data,
                        timeout=self.timeout,
                        headers=headers,
                        params=params,
                    )
                elif result.status_code == 429:  # too many requests
                    sleep(30)
                    result = self._session.request(
                        method,
                        url,
                        data=data,
                        timeout=self.timeout,
                        headers=headers,
                        params=params,
                    )

                if result.status_code not in [200, 201]:
                    raise requests.exceptions.RequestException(
                        f"ERROR: {result.status_code} {result.reason} @ {url}: {result.content}"
                    )

                return result
            except requests.exceptions.RequestException as e:
                logger.error(f"ERROR: {e}", exc_info=True)
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

    def post(self, url, data, headers={}, files=None):
        """
        POST request for creating new objects. If you are uploading a file, pass the file object in the files parameter.
        :param data: Typically a dictionary, but if a file is being uploaded, it should be a string such as data = {'data': '{"description": "My Image", "ordering": "1", "itemID": "123"}'}
        :param files: should be a requests file object like {'image': (filename, file, 'image/jpeg')}
        :param headers: should be left blank unless you want to override the default headers
        """
        response = self._run_method(
            "POST", url, data=data, files=files, headers=headers
        )
        logger.debug(f"POST:Data: {data} \n Headers: {headers} \n Response: {response}")
        return self._handle_response(url, response)

    def _manage_token_refresh(self):
        """Monitors token refresh requirements where needed and refreshes the token if needed. This should be overridden by subclasses to handle the specific API type."""
        return

    def _handle_result(self, res):
        """A helper method to parse the response and return the raw result as json or raise an exception. The result should always be an iterable object, even if it is empty."""
        # This should be overridden by subclasses to handle the specific API type. This actual function probably doesn't work well.
        try:
            result = res.json()
            # attaches the raw json to the result
            return result
        except Exception as e:  # json might be invalid, or store might be down
            e.__docs__ += (
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
            logging.warning(
                f"WARNING: TOKEN ERROR {res.status_code} {res.reason} @ {url}: {res.content}"
            )
            logging.debug(f"Headers are: {self._session.headers}")

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
    """
    Class for making OAuth requests on the Lightspeed Retail API
    Provide access_token and token_file if you already have one - it will be refreshed if it expires.
    https://developers.lightspeedhq.com/retail/authentication/authentication-overview/
    Otherwise, you may use fetch_token with the code, context, and scope passed to your application's callback url
    to retrieve an access token.

    PARAMETERS:
    client_id: the client id of your application
    client_secret: the client sekret key of your application
    token_file: Full path to a file to store the access token in. Default: codes.json
    host: the hostname of the Lightspeed API. Default: api.lightspeedapp.com
    api_path: the path to the API. Default: '/API/Account/{}/{}'
    """

    def __init__(
        self,
        account_id,
        client_id,
        client_secret,
        token_file="codes.json",
        host="api.lightspeedapp.com",
        api_path="/API/Account/{}/{}",
    ):
        # Data for setting up OAuth
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file
        self.host = host
        self.api_path = api_path

        # Check Lightspeed documentation for this
        self.access_token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        self.authorization_base_url = (
            "https://cloud.lightspeedapp.com/oauth/authorize.php"
        )
        self.response = None
        # Resource is used to carry the name of the resource being requested in case it is needed elsewhere.
        self.resource = ""
        self.request_counter = 0
        self.refresh_token = ""
        # Timeouts are happening more frequently on Azure, so set connect to 7 seconds and read to 30 seconds
        self.timeout = (10, 30)

        # Add these to handle pagination
        self.count = 0
        self.offset = 1
        self.limit = 100

        # Load the access token from the token file and set properties related to refresh
        self.access_token = ""
        self.token_type = ""
        self.scope = ""
        self.expires_in = 0.0
        self.expires = 0.0

        self._session = requests.Session()
        self._session.headers = {
            "Accept": "application/json",
            "authorization": f"Bearer {self.access_token}",
        }  # I use json, but you can change this to XML if you want. See Data Formats https://developers.lightspeedhq.com/retail/introduction/introduction/

        logging.info(
            f"{self}: Creating new API Connection to (Store: {self.account_id})"
        )

        # OG: But LS does not use anything in the header, so don't need to do anything with this
        # if access_token and store_hash:
        #     self._session.headers.update(self._oauth_headers(client_id, access_token))

        self._last_response = None  # for debugging

        self.rate_limit = {}

        self._manage_token_refresh()

    def full_path(self, url):
        return "https://" + self.host + self.api_path.format(self.account_id, url)

    @staticmethod
    def _oauth_headers(cid, atoken):
        return {"X-Auth-Client": cid, "X-Auth-Token": atoken}

    @staticmethod
    def verify_payload(signed_payload, client_secret):
        """
        Given a signed payload (usually passed as parameter in a GET request to the app's load URL) and a client secret,
        authenticates the payload and returns the user's data, or False on fail.
        Uses constant-time str comparison to prevent vulnerability to timing attacks.
        """
        encoded_json, encoded_hmac = signed_payload.split(".")
        dc_json = base64.b64decode(encoded_json)
        signature = base64.b64decode(encoded_hmac)
        expected_sig = hmac.new(
            client_secret.encode(), base64.b64decode(encoded_json), hashlib.sha256
        ).hexdigest()
        authorised = hmac.compare_digest(signature, expected_sig.encode())
        return json.loads(dc_json.decode()) if authorised else False

    def fetch_token(
        self,
        client_secret,
        code,
        context,
        scope,
        redirect_uri,
        token_url="https://cloud.lightspeedapp.com/oauth/access_token.php",
    ):
        """
        TODO: THIS DOES NOT WORK. Leaving it here if I want to try it again later.
        Fetches a token from given token_url, using given parameters, and sets up session headers for
        future requests.
        redirect_uri should be the same as your callback URL.
        code, context, and scope should be passed as parameters to your callback URL on app installation.
        Raises HttpException on failure (same as Connection methods).
        """
        res = self.post(
            token_url,
            {
                "client_id": self.client_id,
                "client_secret": client_secret,
                "code": code,
                "context": context,
                "scope": scope,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._session.headers.update(
            self._oauth_headers(self.client_id, res["access_token"])
        )
        return res


class RSeriesConnection(OAuthConnection):
    def __init__(
        self,
        account_id,
        client_id,
        client_secret,
        token_file="codes.json",
        host="api.lightspeedapp.com",
        api_path="/API/Account/{}/{}",
    ):
        # run the parent's init
        super().__init__(
            account_id, client_id, client_secret, token_file, host, api_path
        )

    def _manage_token_refresh(self):
        """Confirm if there is a rate limit that needs checked or refreshed before running make_request"""
        # https://developers.lightspeedhq.com/retail/authentication/refresh-token/
        # We are holding the expiration time in the connection, so we can check to see if it is expired
        # If it is expired, then we need to refresh the token
        if time.time() >= self.expires:
            # On initiation, the object checks to see if there are codes (access_token and refresh_token) saved locally. If it finds them, it reads them, assigns them to
            # properties, refreshes them if needed, and returns
            # 1. Check to see if there is token_file already witha refresh token in it
            logging.info(
                f"{self}:TOKEN REFRESH: Hold while the token at {self.token_file} is refreshed..."
            )
            try:
                # write out the codes to a file
                with open(self.token_file, "r") as f:
                    codes = json.load(f)
                    # Your refresh token does not expire, so it is actually the important one.
                    logging.debug(
                        f"{self}:TOKEN REFRESH: Found {self.token_file} \n Codes Contains: {codes}"
                    )
                    # if codes contains an "error" key, then the token is bad and we need to delete the file and throw a FileNotFoundError to recreate the codes
                    if codes.get("error"):
                        logging.warning(f"{self}:TOKEN REFRESH: {codes.get('error')}")

                        raise FileNotFoundError(
                            f"{self}:TOKEN REFRESH: {codes.get('error')}"
                        )

            except FileNotFoundError as err:
                # TODO: Need to add back in the code that checks the environment variables for keys. This should handle both env and file keys
                logging.warning("TOKEN REFRESH: No Codes File Found:{0}".format(err))

                ### OLD CODE: SAving for reference
                # # 2. If there are no keys, it should fire the process to get a temp token, authenticate the user, and write out the creds
                # # For now we are going to do it manually by going to
                # # https://cloud.lightspeedapp.com/oauth/authorize.php?response_type=code&client_id={YOUR CLIENT ID}&scope=employee:all
                # # to obtain the CODE. Paste that CODE (it is in the URL returned) below and run this before the CODE expires (30 seconds)
                # # to get your access token back.
                # # This code only lasts 30 seconds, so hurry and paste yours here and rerun this.
                # CODE = "xxx"
                # # This is the payload defined by the Lightspeed API doc. My code differs from the sample code, but I think their samples have
                # # issues, so mostly I don't use them.
                # payload = {"client_id": self.client_id, "client_secret": self.client_secret, "code": CODE, "grant_type": "authorization_code"}
                # # Send the payload to the API access token URL
                # r = requests.post(self.access_token_url, data=payload)
                # codes = r.json()
                # logging.debug(f"{self}:TOKEN REFRESH:: Got new codes, which are: {codes}")

                # Authorize to Lightspeed API OAuth
                # This will open a browser window to the Lightspeed API OAuth page. You will need to authorize the app and then paste the URL here.
                # You will need access to the terminal to paste the URL here.
                # Should only need to be done once with new connections, or if the codes file is deleted.
                import webbrowser
                from urllib.parse import urlencode, parse_qs

                # Replace these with your actual client_id, client_secret, and redirect_uri
                redirect_uri = "https://127.0.0.1:5000/"  # This should match the redirect URI set in your OAuth application settings

                # Step 1: Request the temporary authorization code

                auth_params = {
                    "response_type": "code",
                    "client_id": self.client_id,
                    "scope": "employee:all",
                    "redirect_uri": redirect_uri,
                }

                # Construct the full authorization URL
                auth_request_url = (
                    f"{self.authorization_base_url}?{urlencode(auth_params)}"
                )

                # Open the authorization URL in the default web browser
                print("Please go to this URL and authorize the application:")
                print(auth_request_url)
                webbrowser.open(auth_request_url)

                # After user authorization, you'll get a 'code' parameter in the redirect URL
                # For this example, we'll assume you manually paste the redirected URL here
                redirected_url = input("Paste the full redirected URL here: ")
                parsed_url = parse_qs(redirected_url.split("?")[1])
                authorization_code = parsed_url.get("code")[0]

                # Step 2: Request the access token

                token_data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                }

                response = requests.post(self.access_token_url, data=token_data)
                response_data = response.json()

                # Print the access token
                if "access_token" in response_data:
                    access_token = response_data["access_token"]
                    print("Access Token:", access_token)
                else:
                    print("Error fetching the access token:", response_data)

                # Save the codes in a file on the local system so we can get them (and refresh them) next time
                with open(self.token_file, "w") as outfile:
                    json.dump(response.json(), outfile, indent=4)

            else:
                # If there are codes, get the refresh token out, and force a refresh the access code
                self.refresh_token = codes["refresh_token"]
                # TODO - This should probably check the expiration but for now I am forcing a refresh. Need to come back and write some checking
                payload = {
                    "refresh_token": self.refresh_token,
                    "client_secret": self.client_secret,
                    "client_id": self.client_id,
                    "grant_type": "refresh_token",
                }
                codes = requests.post(self.access_token_url, data=payload).json()
                logging.debug(
                    f"{self}:TOKEN REFRESH: Requesting new tokend from {self.access_token_url} with payload {payload} \n Response is {codes}"
                )
                self.access_token = codes["access_token"]
                self.token_type = codes["token_type"]
                self.scope = codes["scope"]
                self.expires_in = codes["expires_in"]
                self.expires = time.time() + int(self.expires_in)

                # The data returned in a refresh doesn't include the refresh_token, and we need to update the codes.json file, so rebuild it and write it out to the file
                # TODO - Need to look up the way to append to a dictionary - probably don't need to rebuild the whole thing
                new_codes = {
                    "access_token": codes["access_token"],
                    "expires_in": codes["expires_in"],
                    "token_type": codes["token_type"],
                    "scope": codes["scope"],
                    "refresh_token": self.refresh_token,
                    "last_run": time.time(),
                }
                with open(self.token_file, "w") as outfile:
                    json.dump(new_codes, outfile, indent=4)

                # Now we have nice, fresh codes we can buld the headers property that the API will use
                self._session.headers["authorization"] = f"Bearer {self.access_token}"

                logging.info(
                    f"{self}:TOKEN REFRESH COMPLETE: {new_codes}\nExpires in {self.expires_in} seconds."
                )
        else:
            logging.debug(
                f"{self}:TOKEN REFRESH: Token {self.access_token} is still good for {self.expires - time.time()} seconds."
            )

    def _handle_ratelimits(self, res):
        # Lightspeed R Series uses a leaky bucket algorithm to throttle API calls. Manage it here.
        # https://developers.lightspeedhq.com/retail/introduction/ratelimits/
        if "X-LS-API-Bucket-Level" in res.headers:
            api_drip_rate = float(res.headers["X-LS-API-Drip-Rate"])
            # Since the bucket level comes back as a fraction, we pull it appart to get the pieces we need
            api_bucket_level, api_bucket_size = [
                (float(x)) for x in res.headers["X-LS-API-Bucket-Level"].split("/")
            ]

            logging.debug(
                f"{self}: HANDLE RATELIMITS: Used {api_bucket_level} of {api_bucket_size} , refreshing at {api_drip_rate} and {time.time() - self.expires} sec. left on token."
            )

            if (
                api_bucket_size < api_bucket_level + 10
            ):  # R-Series counts the largest requests as 10, so need to always have 10 available to avoid a 429
                logging.info(
                    f"{self}: HANDLE RATELIMITS:: Bucket is almost full, taking a break."
                )
                sleep(10)

            if (
                time.time() >= self.expires
            ):  # This should never happen because we are checking it before we make the request, but just in case. Probably remove this later
                logging.debug(f"{self}: HANDLE RATELIMITS: Token needs a refresh")
                sleep(2)  # Make sure lightspeed has timed out
                self._manage_token_refresh()
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
                # Loop through the results and add the raw json to each item, which will be converted to a property later
                for new_item, source_item in zip(result, orig_result[self.resource]):
                    new_item["json"] = source_item

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
                result["json"] = orig_result[self.resource]
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
    def _handle_result(self, res) -> list:
        """Returns a list of dicts, and None if there is no result."""
        orig_result = res.json()
        try:
            # 1) In eCom it is under the resource type {'brand': {'id': 2734938, 'createdAt':  or {'product': {'id': 58526124, 'createdAt': '2023-07-23T17:32:52+00:00', 'updatedAt': '2023-07-23T17:51:13+00:00', 'isVisible': True, 'visibility': 'auto', 'hasMatrix': False, 'data01': '91 pts', 'data02': '', 'data03': '', ...}}
            #  Searches with no results return: {'products': []}
            # This strips off whatever is the name resulting object and return the dict so that Mapping can convert it to a resource object.
            # Cseries returns the singular form of the resource name in the response (not the pluralized name from the endpoint). So resetting resource to the singular name by pulling it from the response
            self.resource = list(orig_result.keys())[0]
            # and then pull the actual result from the response
            result = orig_result[self.resource]

            # per our new standard, if there is no result return an empty list
            if len(result) == 0:
                self.json = {}
                result = []
            # If the original call was a get or update, return the result as one dict (which will be converted later to an object), but if it was list(), or list_all() return a list of dicts (which will be converted to a list of objects)
            else:
                # If the original call was a .get() or .update() return the result as one dict (which will be converted later to an object), but if it was list(), or list_all() return a list of one dict (which will be converted to a list of one object)
                # PROBABLY BREAKING SOMETHING HERE - C-Series probably doesn't know the difference between a get and a list so may cause issues
                if isinstance(result, dict):
                    result["json"] = orig_result[self.resource]
                else:
                    # Loop through the results and add the raw json to each item, which will be converted to a property later
                    for new_item, source_item in zip(
                        result, orig_result[self.resource]
                    ):
                        new_item["json"] = source_item

            return result

        except Exception as e:  # json might be invalid, or store might be down
            e.__doc__ += (
                " (_handle_response failed to decode JSON: " + str(res.content) + ")"
            )


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
    """
    Makes a connection to the Lightspeed X-Series API with Oauth
    XSeries as several differences from the eCom API including:
        - Supports both a personal token and an Oauth token
        - Requires a different endpoint including version number
        - Only supports JSON
        - Has a different rate limiting algorithm which is used on both personal and Oauth tokens
        - Expects a different header including a User Agent

    """

    def __init__(self, host, auth, api_path="/api/{}{}", format=""):
        self.host = host
        self.api_path = api_path
        # Lightspeed will return json or xml depending on extension. For simplicity, defining it at the object not method.
        self.format = format

        self.response = None
        self.request_counter = 0
        self.resource = ""

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
        return "https://" + self.host + self.api_path.format(self.api_version, url)

    def _handle_response(self, url, res, suppress_empty=True):
        """
        Handles XSeries specific json formats of responses, standardizing them for the Mapping class
        """
        result = Connection._handle_response(self, url, res, suppress_empty)
        # Main handling of the response will have already failed if there is an error, so we can assume it is good
        # X-Series returns json like {'includes': None, 'data': {'id': '7eb310ba-...
        # So pull out only the data key
        try:
            if "includes" in res.json():
                self.includes = res.json()["includes"]
            if "version" in res.json():
                self.page_min = res.json()["version"]["min"]
                self.page_max = res.json()["version"]["max"]
            if "data" in res.json():
                result = res.json()["data"]

        except Exception as e:  # json might be invalid, or store might be down
            e.message += (
                " (_handle_response failed to decode JSON: " + str(res.content) + ")"
            )
            raise  # TODO better exception

        return result


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
