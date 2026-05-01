from ..base import *
from .rseriesbase import *


class RSeriesSalelines(RSeriesApiResource, CountableApiResource):
    """LS Retail Saleline API Resource. https://developers.lightspeedhq.com/retail/endpoints/SaleLine/"""
    resource_name = 'SaleLine'
    resource_id = 'saleLineID'