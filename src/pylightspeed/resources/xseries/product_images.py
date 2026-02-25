# https://docs.vendhq.com/reference/

from ..base import *
from .xseriesbase import *


class XSeriesProductImages(XSeriesApiResource, ListableApiResource, CreateableApiResource,
               UpdateableApiResource, DeleteableApiResource,
               CollectionDeleteableApiResource, CountableApiResource):
    resource_name = 'product_images'