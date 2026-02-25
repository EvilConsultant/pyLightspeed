from ..base import *


class RSeriesOrders(ListableRetailApiResource, CountableApiResource):
    """LS Retail Order API Resource. https://developers.lightspeedhq.com/retail/endpoints/Order/"""

    resource_name = "Order"
    resource_id = "orderID"
