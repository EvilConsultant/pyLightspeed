from ..base import *
from .rseriesbase import *


class RSeriesCustomers(RSeriesApiResource, CreateableApiResource, UpdateableRetailApiResource, DeleteableApiResource):
    resource_name = "Customer"
    resource_id = "customerID"

    def contacts(self, id=None):
        """Returns a list of contacts for the customer based on calling the Customer endpoint.
        Doc here: https://developers.lightspeedhq.com/ecom/endpoints/productimage/

        Parameters
        ----------
        id : int
            The product id."""

        if id:
            return Contacts.fetch(self.itemID, id, connection=self._connection)
        else:
            return Contacts.list_all(self.itemID, connection=self._connection)


class Contacts(ListableApiSubResource):
    resource_name = "Contact"
    parent_resource = "Customer"
    parent_key = "customerID"
    count_resource = "Customer/Contact"
