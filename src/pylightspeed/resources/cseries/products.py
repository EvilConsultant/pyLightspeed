# Ecom: Products Endpoint
# https://developers.lightspeedhq.com/ecom/endpoints/product/

# FILTERS
# brand	Retrieve the products that have a specific brand based on the brandID.
# limit	Number of results.
# (default:50) (maximum:250)
# page	Page to show.
# (default:1)
# since_id	Restrict results to after the specified ID.
# (default:0)
# created_at_min	Show products created after date.
# (format: YYYY-MM-DD HH:MM:SS)
# created_at_max	Show products created before date.
# (format: YYYY-MM-DD HH:MM:SS)
# updated_at_min	Show products last updated after date.
# (format: YYYY-MM-DD HH:MM:SS)
# updated_at_max	Show products last updated before date.
# (format: YYYY-MM-DD HH:MM:SS)
# fields	Comma-separated list of fields to include in the response.
# (format: id,createdAt)

from ..base import *


class CSeriesProducts(
    ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource, CollectionDeleteableApiResource, CountableApiResource
):
    resource_name = "products"

    def images(self, id=None):
        """Returns a list of images for the product based on calling the ProductImage endpoint.
        Doc here: https://developers.lightspeedhq.com/ecom/endpoints/productimage/

        Parameters
        ----------
        id : int
            The product id."""

        if id:
            return CSeriesProductImages.get(self.id, id, connection=self._connection)
        else:
            return CSeriesProductImages.listall(self.id, connection=self._connection)


class CSeriesProductImages(
    ListableApiSubResource,
    CreateableApiSubResource,
    UpdateableApiSubResource,
    DeleteableApiSubResource,
    CollectionDeleteableApiSubResource,
    CountableApiSubResource,
):
    resource_name = "images"
    parent_resource = "products"
    parent_key = "product_id"
    count_resource = "products/images"


class CSeriesProductAttributes(
    ListableApiSubResource,
    CreateableApiSubResource,
    UpdateableApiSubResource,
    DeleteableApiSubResource,
    CollectionDeleteableApiSubResource,
    CountableApiSubResource,
):
    resource_name = "attributes"
    parent_resource = "products"
    parent_key = "id"


class CSeriesProductFilterValues(
    ListableApiSubResource,
    CreateableApiSubResource,
    UpdateableApiSubResource,
    DeleteableApiSubResource,
):
    resource_name = "filtervalues"
    parent_resource = "products"
    parent_key = "id"
    count_resource = "products/{}/filtervalues"
