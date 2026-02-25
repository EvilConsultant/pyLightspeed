from ..base import *


class RSeriesSales(ListableRetailApiResource, CountableApiResource):
    """LS Retail Sales API Resource. https://developers.lightspeedhq.com/retail/endpoints/Sale/"""
    resource_name = 'Sale'
    resource_id = 'saleID'