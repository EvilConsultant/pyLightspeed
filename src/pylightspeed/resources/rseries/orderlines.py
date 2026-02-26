from ..base import *
from .rseriesbase import *


class RSeriesOrderlines(RSeriesApiResource, CountableApiResource):
    """LS Retail Order API Resource. https://developers.lightspeedhq.com/retail/endpoints/Order/"""

    resource_name = "OrderLine"
    resource_id = "orderLineID"
