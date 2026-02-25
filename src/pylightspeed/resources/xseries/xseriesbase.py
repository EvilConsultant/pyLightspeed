from ..base import *


class XSeriesApiResource(ApiResource):
    # The various APIs and endpoints of Lightspeed have different names for important fields. This class gives us the
    # flexibility to allow us to override the default values for the resource name, id, and created_at/updated_at fields.
    # X Series uses id, created_at, and updated_at for all endpoints, so we can set that here.
    resource_id = "id"
    created_at = "created_at"
    updated_at = "updated_at"
    api_version = "2.0"

    @classmethod
    def _paginate09(cls, connection=None, **params):
        """Not implemented. Here when needed for compatibility with the API 0.9 pagination process."""
        # TODO: Implement this. For now, just try the 2.0 pagination process if this is called.
        return cls._paginate2(connection=connection, **params)

    @classmethod
    def _paginate2(cls, connection=None, **params):
        """Returns the next page of resources, or None if there are no more pages based on the API 2.0 pagination process."""
        params["after"] = connection.page_max
        return cls.page(connection=connection, **params)

    @classmethod
    def paginate(cls, connection=None, **params):
        """Returns the next page using the API pagination method of the correct version."""
        if connection.api_version == "2.0":
            return cls._paginate2(connection=connection, **params)

            # https://x-series-api.lightspeedhq.com/docs/products_image_uploads_code_sample_python_requests

    @classmethod
    def listall(cls, connection=None, **params):
        """
        Returns all of the resources in a list, automatically handling pagination.
        Use this if you need to pull all of the resources for exports or something.
        Otherwise, consider using the iterall method.
        """
        # Note: page_max is created and set as part of connection.XSeriesPersonalConnection._handle_result
        all_resources = []

        # try:
        response = cls.page(connection=connection, **params)
        all_data = response

        if (
            connection.page_max == 0 or connection.has_next == False
        ):  # X has multiple pagination methods - need to make sure handle response is sorting through them correctly
            return all_data  # Should probably do something better here. If the filter is returning no rows this is failing - need to handle more gracefully.

        while response:  # Xseries returns None if there are no more pages, and the connection._handleresponse returns an empty list if there are no more pages
            response = cls.paginate(connection=connection, **params)
            if (
                response is not None
            ):  # Added this because got a response of None and it was breaking the loop. Response should never be None - connection._make_request should always return a list
                all_data.extend(response)
            else:
                break

        return all_data
