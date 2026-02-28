class HttpException(Exception):
    """
    Class for representing http errors. Contains the response.
    """

    def __init__(self, msg, res):
        super(Exception, self).__init__(msg)
        self.response = res

    @property
    def status_code(self):
        return self.response.status_code

    @property
    def headers(self):
        return self.response.headers

    @property
    def content(self):
        return self.response.content


# 204
class EmptyResponseWarning(HttpException):
    pass


# 4xx codes
class ClientRequestException(HttpException):
    pass


# 422 from X-Series
class UnprocessableEntity(HttpException):
    pass


# 401
class RateLimitingException(ClientRequestException):
    @property
    def retry_after(self):
        return self.response.headers["X-Rate-Limit-Time-Reset-Ms"]

    pass


class Unauthorised(ClientRequestException):
    pass


# class AccessForbidden(ClientRequestException): pass
# class ResourceNotFound(ClientRequestException): pass
# class ContentNotAcceptable(ClientRequestException): pass


# 5xx codes
class ServerException(HttpException):
    pass


# class ServiceUnavailable(ServerException): pass
# class StorageCapacityError(ServerException): pass
# class BandwidthExceeded(ServerException): pass

# 405 and 501 - still just means the client has to change their request
# class UnsupportedRequest(ClientRequestException, ServerException): pass


# 3xx codes
class RedirectionException(HttpException):
    pass


class NotLoggedInException(Exception):
    pass


class MissingTokenError(Exception):
    """Raised when no valid OAuth token is available and automatic acquisition is not possible.

    Typically raised by a Connection's ``_manage_token_refresh()`` when the token store is
    empty or the stored token is corrupt.  Callers should use the connection's
    ``get_authorization_url()`` / ``exchange_code_for_token()`` helpers (or a CLI setup
    script) to obtain an initial token and persist it via a :class:`TokenStore`.
    """
    pass
