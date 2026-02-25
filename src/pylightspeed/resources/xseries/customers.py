# https://docs.vendhq.com/reference/

from ..base import *
from .xseriesbase import *


class XSeriesCustomers(XSeriesApiResource, ListableApiResource, CreateableApiResource,
               UpdateableApiResource, DeleteableApiResource,
               CollectionDeleteableApiResource, CountableApiResource):
    resource_name = 'customers'