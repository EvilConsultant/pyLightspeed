from ..base import *


class RSeriesOrderlines(ListableRetailApiResource, CountableApiResource):
    """LS Retail Order API Resource. https://developers.lightspeedhq.com/retail/endpoints/Order/"""

    resource_name = "OrderLine"
    resource_id = "orderLineID"
