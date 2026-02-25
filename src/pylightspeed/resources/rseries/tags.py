from ..base import *


class RSeriesTags(ListableApiResource, CountableApiResource, UpdateableApiResource, CreateableApiResource, DeleteableApiResource):
    resource_name = 'tags'


class RSeriesTagProducts(ListableApiSubResource, CountableApiSubResource, UpdateableApiSubResource, CreateableApiSubResource, DeleteableApiSubResource):
    resource_name = 'products'
    parent_resource = 'tags'
    parent_key = 'id'
    count_resource = 'tags/products'