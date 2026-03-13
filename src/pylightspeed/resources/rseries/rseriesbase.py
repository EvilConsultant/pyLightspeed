from ..base import *


class RSeriesApiResource(ListableApiResource):
    """Base class for all Lightspeed R-Series API resources.

    R-Series uses a different pagination style, field naming, and filter
    syntax to the other Lightspeed series (C / X / E).  This class
    centralises all of those differences so individual resource classes
    (Items, Vendors, …) stay clean.

    Replaces the legacy ``ListableRetailApiResource`` mixin from base.py.
    """

    # R-Series field name overrides (the base uses createdAt / updatedAt)
    created_at = "createTime"
    updated_at = "timeStamp"

    # R-Series pagination defaults
    # https://developers.lightspeedhq.com/retail/introduction/pagination/
    count = 0
    limit = 100
    offset = 0

    # ------------------------------------------------------------------
    # Pagination — R-Series uses offset/limit, not page
    # ------------------------------------------------------------------

    @classmethod
    def iter_all(cls, connection=None, **kwargs):
        """Auto-paging generator — yields each object one at a time.

        R-Series edition: uses offset/limit pagination (not page-based).
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

        def _all_responses():
            offset = 1  # one-based
            limit = 100
            params = kwargs.copy()

            while True:
                params.update(offset=offset, limit=limit)
                rsp = cls._make_request("GET", cls._get_all_path(), connection, params=params)
                if rsp:
                    yield rsp
                    offset = connection.offset + connection.limit
                else:
                    yield []  # handle empty result sets
                    break

        if not (limit or offset):
            for rsp in _all_responses():
                for obj in rsp:
                    yield cls._create_object(obj, connection=connection)
        else:
            response = cls._make_request("GET", cls._get_all_path(), connection, params=kwargs)
            if response is None or len(response) == 0:
                return
            for obj in cls._create_object(response, connection=connection):
                yield obj

    @classmethod
    def iter(cls, connection=None, yield_per_item=True, **params):
        """Generator that yields resources from the server, handling pagination.

        If *yield_per_item* is True (default), yields each item individually.
        If False, yields a whole page at once.
        """
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)

        while True:
            params["limit"] = limit
            params["offset"] = offset

            response = cls.page(connection=connection, **params)

            if not response or connection.count == "0":
                break

            if yield_per_item:
                for item in response:
                    yield item
            else:
                yield response

            offset += limit

            if connection.count < offset:
                break

    @classmethod
    def list_all(cls, connection=None, **params):
        """Return all resources as a list, auto-handling R-Series pagination."""
        try:
            limit = params["limit"]
        except KeyError:
            limit = 100

        try:
            offset = params["offset"]
        except KeyError:
            offset = None

        response = cls.page(connection=connection, **params)
        all_data = response

        if connection.count == "0":
            return all_data

        while connection.count >= (connection.offset + connection.limit):
            params["offset"] = connection.offset + connection.limit
            response = cls.page(connection=connection, **params)
            if response is not None:
                all_data.extend(response)
            else:
                break

        return all_data

    # ------------------------------------------------------------------
    # Incremental sync
    # ------------------------------------------------------------------

    @classmethod
    def sync_records(cls, connection=None, since=None, **params):
        """Yield records created or modified since *since* (or all if None).

        R-Series filter format: ``fieldName:>,ISOvalue``.  Uses ``updated_at``
        (``timeStamp`` by default) so both newly created records *and* edits
        are captured in a single pass.

        Individual resource classes can override ``updated_at`` where the
        endpoint uses a non-standard field name (e.g. ``RSeriesVendors``
        overrides it to ``timeStamp`` because ``createTime`` is absent).
        """
        if since is not None:
            params[cls.updated_at] = f">,{since.isoformat()}"
        yield from cls.iter(yield_per_item=True, connection=connection, **params)


class DeleteableRSeriesApiResource(DeleteableApiResource):
    def _delete_path(self):
        return "%s/%s" % (self.resource_name, getattr(self, self.resource_id))
