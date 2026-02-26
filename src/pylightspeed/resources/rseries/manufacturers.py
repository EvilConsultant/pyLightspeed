from ..base import *
from .rseriesbase import *


class RSeriesManufacturers(RSeriesApiResource, CountableApiResource, CreateableApiResource, UpdateableRetailApiResource):
    """LS Retail Manufacturer API Resource. https://developers.lightspeedhq.com/retail/endpoints/Manufacturer/"""
    resource_name = 'Manufacturer'
    resource_id = 'manufacturerID'