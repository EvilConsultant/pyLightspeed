from ..base import *


class ESeriesApiResource(ApiResource):
    """
    Represents an API resource for e Series in Lightspeed.

    This class provides the flexibility to override default values for the resource name, id, and created_at/updated_at fields.
    e Series uses id, created, and updated for all endpoints.

    Attributes:
        resource_name (str): The name of the resource.
        resource_id (str): The id of the resource.
        created_at (str): The field name for the created timestamp.
        updated_at (str): The field name for the updated timestamp.
        api_version (str): The version of the API.

    Methods:
        N/A
    """

    resource_name = "items"
    resource_id = "id"
    created_at = "created"
    updated_at = "updated"
    api_version = "v3"

    @classmethod
    def paginate(cls, connection=None, **params):
        """Returns the next page of resources based on the offset parameter."""
        offset = connection.offset + connection.limit
        return cls.page(connection=connection, offset=offset, **params)

    @classmethod
    def listall(cls, connection=None, **params) -> list:
        """
        Returns all of the resources in a list, automatically handling pagination.
        Use this if you need to pull all of the resources for exports or something.
        Otherwise, consider using the iterall method. Note: pagination parameters are
        handled/set by the connection._handle_response method.

        Args:
            connection (LightspeedESeriesConnection): The connection to the API.
            **params: Additional parameters to pass to the API.

        Returns:
            list: A list of all the resources.
        """

        all_data = []

        # try:
        response = cls.page(connection=connection, **params)
        all_data = response

        if connection.count == 0 or connection.has_next == False:
            return all_data

        while response:  # connection._handleresponse returns an empty list if there are no more pages
            response = cls.paginate(connection=connection, **params)
            if response is not None:
                all_data.extend(response)
            else:
                break

        return all_data  # Not sending this to _create_object because the .all() method already does that
