import requests


class Mapping(dict):
    """
    Mapping

    provides '.' access to dictionary keys
    """

    def __init__(self, mapping, *args, **kwargs):
        """
        Create a new mapping. Filters the mapping argument
        to remove any elements that are already methods on the
        object.

        For example, Orders retains its `coupons` method, instead
        of being replaced by the dict describing the coupons endpoint
        """

        mapping = mapping or {}

        filter_args = {k: mapping[k] for k in mapping if k not in dir(self)}
        self.__dict__ = self

        dict.__init__(self, filter_args, *args, **kwargs)

    def __str__(self):
        """
        Display as a normal dict, but filter out underscored items first
        """
        return str({k: self.__dict__[k] for k in self.__dict__ if not k.startswith("_")})

    def __repr__(self):
        return "<%s at %s, %s>" % (type(self).__name__, hex(id(self)), str(self))


class ApiResource(Mapping):
    # Since these objects have to adapt based on the different models and data structures used by Lightspeed, we build in
    # flexibility to allow us to override the default values for the resource name, id, and created_at/updated_at fields.
    resource_name = ""  # The identifier which describes this resource in urls
    resource_id = "id"
    created_at = "createdAt"
    updated_at = "updatedAt"

    @classmethod
    def _create_object(cls, response, connection=None):
        """
        Process a dict from the response into an object with dot access to properties
        """
        if response and not isinstance(response, dict):
            return [cls(obj, _connection=connection) for obj in response]
        elif (
            response is None or len(response) == 0
        ):  # added this to try to stop items from being created when there is no data, and then trying to iterate over the _connection attribute
            return []
        else:
            return cls(response, _connection=connection)

    @classmethod
    def _make_request(cls, method, url, connection, data=None, params=None, headers=None, files=None):
        return connection.make_request(method, url, data, params, headers, files)

    @classmethod
    def _get_path(cls, id):
        return "%s/%s" % (cls.resource_name, id)

    @classmethod
    def get(cls, id, connection=None, **params):
        response = cls._make_request("GET", cls._get_path(id), connection, params=params)
        return cls._create_object(response, connection=connection)

    def nested_json_to_attr(self):
        """
        Override this to map any nested properties returned by the API to something simpler. For example,
        mapping a nested property like `self["address"]["street"]` to `self["street"]`.
        """
        pass

    def as_dict(self):
        """Return a flat, predictable dict of this resource's scalar data.

        Calls ``nested_json_to_attr()`` first so any derived attributes
        (e.g. ``price_default`` on RSeries Items) are populated before
        extraction.

        Keys use the API's own field names. Only scalar values (str, int,
        float, bool, None) are included — nested dicts and lists are omitted.
        Call ``dict(self)`` directly if you need the full nested structure.
        """
        self.nested_json_to_attr()
        result = {}
        for key, val in self.items():
            if key.startswith("_"):
                continue
            if isinstance(val, (str, int, float, bool)) or val is None:
                result[key] = val
        return result


class ApiSubResource(ApiResource):
    parent_resource = ""
    parent_key = ""

    @classmethod
    def _get_path(cls, id, parentid):
        return "%s/%s/%s/%s" % (cls.parent_resource, parentid, cls.resource_name, id)

    @classmethod
    def get(cls, parentid, id, connection=None, **params):
        response = cls._make_request("GET", cls._get_path(id, parentid), connection, params=params)
        return cls._create_object(response, connection=connection)

    def parent_id(self):
        return self[self.parent_key]


class CreateableApiResource(ApiResource):
    @classmethod
    def _create_path(cls):
        return cls.resource_name

    @classmethod
    def create(cls, connection=None, **params):
        response = cls._make_request("POST", cls._create_path(), connection, data=params)
        return cls._create_object(response, connection=connection)

    @classmethod
    def create_bulk(cls, connection=None, **params):
        response = cls._make_request("POST", f"{cls._create_path()}/bulk", connection, data=params)
        return cls._create_object(response, connection=connection)


class CreateableApiSubResource(ApiSubResource):
    @classmethod
    def _create_path(cls, parentid):
        return "%s/%s/%s" % (cls.parent_resource, parentid, cls.resource_name)

    @classmethod
    def create(cls, parentid, connection=None, **params):
        response = cls._make_request("POST", cls._create_path(parentid), connection, data=params)
        return cls._create_object(response, connection=connection)

    @classmethod
    def create_image(cls, parentid, image_url, connection=None, **params):
        """Add an image from a url to an endpoint."""
        file = requests.get(image_url).content
        fileload = {"image": file}

        response = cls._make_request("POST", cls._create_path(parentid), connection, params=params, files=fileload)
        return cls._create_object(response, connection=connection)


class ListableApiResource(ApiResource):
    @classmethod
    def _get_all_path(cls):
        return cls.resource_name

    @classmethod
    def page(cls, connection=None, **params):
        """
        Returns first page if no params passed in as a list.
        """

        request = cls._make_request("GET", cls._get_all_path(), connection, params=params)
        return cls._create_object(request, connection=connection)

    @classmethod
    def paginate(cls, connection=None, **params):
        """Returns the next page of resources, or None if there are no more pages based on the API 2.0 pagination process."""
        return cls.page(connection=connection, **params)

    @classmethod
    def get_list(cls, ids, connection=None, **params):
        """
        takes a list of ids and returns a list of objects
        """
        request = []
        for id in ids:
            request.append(cls._make_request("GET", cls._get_path(id), connection, params=params))
        return cls._create_object(request, connection=connection)

    @classmethod
    def listall(cls, connection=None, **params):
        """
        Returns all of the resources in a list, automatically handling pagination.
        Use this if you need to pull all of the resources for exports or something.
        Otherwise, consider using the iterall method.
        """
        all_resources = []
        page = 1
        # Ecommerce API only defaults to 50 resources per page with a max of 250, so we'll set the default to 250 unless otherwise specified
        try:
            limit = params["limit"]
        except KeyError:
            if hasattr(connection, "limit"):
                limit = connection.limit
            else:
                limit = 250

        while True:
            response = cls.paginate(connection=connection, limit=limit, page=page, **params)
            if response is None:
                return []
            all_resources.extend(response)
            if len(response) < limit:
                break
            page += 1
        return all_resources  # Not sending this to _create_object because the .all() method already does that

    @classmethod
    def iterall(cls, connection=None, **kwargs):
        """
        Returns a autopaging generator that yields each object returned one by one.
        """

        try:
            limit = kwargs["limit"]
        except KeyError:
            limit = None

        try:
            page = kwargs["page"]
        except KeyError:
            page = None

        def _all_responses():
            page = 1  # one based
            params = kwargs.copy()

            while True:
                params.update(page=page, limit=250)
                rsp = cls._make_request("GET", cls._get_all_path(), connection, params=params)
                if rsp:
                    yield rsp
                    page += 1
                else:
                    yield []  # needed for case where there is no objects
                    break

        if not (limit or page):
            for rsp in _all_responses():
                for obj in rsp:
                    yield cls._create_object(obj, connection=connection)

        else:
            response = cls._make_request("GET", cls._get_all_path(), connection, params=kwargs)
            # Added to try to handle the case where there are no objects returned. Without this, interators are picking up the connection object and trying to iterate over that.
            if response is None or len(response) == 0:
                return
            for obj in cls._create_object(response, connection=connection):
                yield obj

    @classmethod
    def sync_records(cls, connection=None, since=None, **params):
        """Return all records, optionally filtered to those updated since *since*.

        C / X / E series edition — uses ``updated_at_min`` filter convention.
        Returns a list (same contract as ``listall``).

        For R-Series resources, see ``RSeriesApiResource.sync_records``
        which uses the RSeries filter syntax and streams results.
        """
        if since is not None:
            params["updated_at_min"] = since.strftime("%Y-%m-%d %H:%M:%S")
        return cls.listall(connection=connection, **params)


# This class is superseded by RSeriesApiResource in rseries/rseriesbase.py.
# Kept here for backwards compatibility with any external code that inherits
# from it directly.  New code should use RSeriesApiResource instead.
class ListableRetailApiResource(ListableApiResource):
    """Deprecated — use ``RSeriesApiResource`` from rseries.rseriesbase instead.

    This class remains for backwards compatibility.  Its pagination logic
    has been consolidated into ``RSeriesApiResource``.  All built-in RSeries
    resource classes now inherit from ``RSeriesApiResource`` directly.
    """

    created_at = "createTime"
    updated_at = "timeStamp"

    # Properties to manage pagination
    count = 0
    limit = 100  # https://developers.lightspeedhq.com/retail/introduction/pagination/
    offset = 0

    @classmethod
    def iterall(cls, connection=None, **kwargs):
        """
        Returns an autopaging generator that yields each object returned one by one.

        :param connection: Connection object (optional) - the connection object to use for making the request
        :param limit: int (optional) - the number of objects to return per page
        :param offset: int (optional) - the number of objects to skip before returning objects
        :param page: bool (optional) - if True, will return a whole page of objects as the iterator; if False, will return one object at a time

        :return: Generator - a generator that yields each object returned one by one
        """

        try:
            limit = kwargs["limit"]
        except KeyError:
            limit = 100

        try:
            offset = kwargs["offset"]
        except KeyError:
            offset = None

        try:
            page = kwargs["page"]
        except KeyError:
            page = None

        # TODO: This is not handling the @attributes which contains the counts and the pagination information. Need to figure out how to get this information in here.
        def _all_responses():
            offset = 1  # one based
            limit = 100
            params = kwargs.copy()

            while True:
                params.update(offset=offset, limit=limit)
                rsp = cls._make_request("GET", cls._get_all_path(), connection, params=params)
                if rsp:
                    yield rsp
                    offset = connection.offset + connection.limit
                else:
                    yield []  # needed for case where there are no objects
                    break

        if not (limit or offset):
            for rsp in _all_responses():
                for obj in rsp:
                    yield cls._create_object(obj, connection=connection)

        else:
            response = cls._make_request("GET", cls._get_all_path(), connection, params=kwargs)
            # Added to try to handle the case where there are no objects returned, but we still need a list to iterate over. Without this, iterators are picking up the connection object and trying to iterate over that.
            if response is None or len(response) == 0:
                return

            for obj in cls._create_object(response, connection=connection):
                yield obj

    @classmethod
    def iter(cls, connection=None, yield_per_item=True, **params):
        """
        Generator function that yields resources from the server, handling pagination.
        If yield_per_item is True, yields each item one at a time.
        If yield_per_item is False, yields the whole page at once.
        """

        limit = params.get("limit", 100)  # LS max is 100
        offset = params.get("offset", 0)

        while True:
            params["limit"] = limit
            params["offset"] = offset

            # Fetch the current page of results
            response = cls.page(connection=connection, **params)

            # If there's no data or count is 0, stop the iterator
            if not response or connection.count == "0":
                break

            if yield_per_item:
                # Yield each item in the current page of results
                for item in response:
                    yield item
            else:
                # Yield the whole page at once
                yield response

            # Prepare for the next page
            offset += limit

            # Stop if we've fetched all results
            if connection.count < offset:
                break

    @classmethod
    def listall(cls, connection=None, **params):
        """
        Returns all of the resources in a list, automatically handling pagination.
        Use this if you need to pull all of the resources for exports or something.
        Otherwise, consider using the iterall method.
        """

        try:
            limit = params["limit"]
        except KeyError:
            limit = 100  # LS max is 100

        try:
            offset = params["offset"]
        except KeyError:
            offset = None

        all_resources = []

        # try:

        # response = cls._make_request("GET", cls._get_all_path(), connection, params=params)
        response = cls.page(connection=connection, **params)
        all_data = response

        if connection.count == "0":
            return all_data  # Should probably do something better here. If the filter is returning no rows this is failing - need to handle more gracefully.

        while connection.count >= (connection.offset + connection.limit):
            params["offset"] = connection.offset + connection.limit
            # response = cls._make_request("GET", cls._get_all_path(), connection, params=params)
            # Messing with this because it looks like listall() is not returning a list of objects, but a dict? Has it always been doing this?
            response = cls.page(connection=connection, **params)
            if (
                response is not None
            ):  # Added this because got a response of None and it was breaking the loop. Response should never be None - connection._make_request should always return a list
                all_data.extend(response)
            else:
                break

        return all_data


class ListableApiSubResource(ApiSubResource):
    @classmethod
    def _get_all_path(cls, parentid=None):
        # Not all sub resources require a parent id.  Eg: /api/v2/products/skus?sku=<value>
        if parentid:
            return "%s/%s/%s" % (cls.parent_resource, parentid, cls.resource_name)
        else:
            return "%s/%s" % (cls.parent_resource, cls.resource_name)

    @classmethod
    def page(cls, parentid=None, connection=None, **params):
        response = cls._make_request("GET", cls._get_all_path(parentid), connection, params=params)
        return cls._create_object(response, connection=connection)


class UpdateableApiResource(ApiResource):
    def _update_path(self):
        return "%s/%s" % (self.resource_name, self.id)

    def update(self, **updates):
        response = self._make_request("PUT", self._update_path(), self._connection, data=updates)
        return self._create_object(response, connection=self._connection)


class UpdateableRetailApiResource(UpdateableApiResource):
    def _update_path(self):
        return "%s/%s" % (self.resource_name, getattr(self, self.resource_id))


class UpdateableApiSubResource(ApiSubResource):
    def _update_path(self):
        return "%s/%s/%s/%s" % (self.parent_resource, self.parent_id(), self.resource_name, self.id)

    def update(self, **updates):
        response = self._make_request("PUT", self._update_path(), self._connection, data=updates)
        return self._create_object(response, connection=self._connection)


class DeleteableApiResource(ApiResource):
    def _delete_path(self):
        return "%s/%s" % (self.resource_name, self.id)

    def delete(self):
        return self._make_request("DELETE", self._delete_path(), self._connection)


class DeleteableApiSubResource(ApiSubResource):
    def _delete_path(self):
        return "%s/%s/%s/%s" % (self.parent_resource, self.parent_id(), self.resource_name, self.id)

    def delete(self):
        return self._make_request("DELETE", self._delete_path(), self._connection)


class CollectionDeleteableApiResource(ApiResource):
    @classmethod
    def _delete_all_path(cls):
        return cls.resource_name

    @classmethod
    def delete_all(cls, connection=None):
        return cls._make_request("DELETE", cls._delete_all_path(), connection)


class CollectionDeleteableApiSubResource(ApiSubResource):
    @classmethod
    def _delete_all_path(cls, parentid):
        return "%s/%s/%s" % (cls.parent_resource, parentid, cls.resource_name)

    @classmethod
    def delete_all(cls, parentid, connection=None):
        return cls._make_request("DELETE", cls._delete_all_path(parentid), connection)


class CountableApiResource(ApiResource):
    @classmethod
    def _count_path(cls):
        return "%s/count" % (cls.resource_name)

    @classmethod
    def count(cls, connection=None, **params):
        response = cls._make_request("GET", cls._count_path(), connection, params=params)
        return response["count"]


class CountableApiSubResource(ApiSubResource):
    # Account for the fairly common case where the count path doesn't include the parent id
    count_resource = None

    @classmethod
    def _count_path(cls, parentid=None):
        if parentid is not None:
            return "%s/%s/%s/count" % (cls.parent_resource, parentid, cls.resource_name)
        elif cls.count_resource is not None:
            return "%s/count" % (cls.count_resource)
        else:
            # misconfiguration
            raise NotImplementedError("Count not implemented for this resource.")

    @classmethod
    def count(cls, parentid=None, connection=None, **params):
        response = cls._make_request("GET", cls._count_path(parentid), connection, params=params)
        return response["count"]
