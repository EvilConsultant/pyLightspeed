from ..base import *
from .rseriesbase import *


class RSeriesOrders(RSeriesApiResource, CountableApiResource):
    """LS Retail Order API Resource. https://developers.lightspeedhq.com/retail/endpoints/Order/"""

    resource_name = "Order"
    resource_id = "orderID"
