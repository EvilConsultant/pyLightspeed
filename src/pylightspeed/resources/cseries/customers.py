from ..base import *


class CSeriesCustomers(ListableApiResource, UpdateableApiResource, CreateableApiResource, CountableApiResource):
    """LS Ecom Customers API Resource. https://developers.lightspeedhq.com/ecom/endpoints/customer/"""
    resource_name = 'customers'