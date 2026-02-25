from ..base import *


class RSeriesManufacturers(ListableRetailApiResource, UpdateableRetailApiResource, CreateableApiResource, CountableApiResource):
    """LS Retail Manufacturer API Resource. https://developers.lightspeedhq.com/retail/endpoints/Manufacturer/"""
    resource_name = 'Manufacturer'
    resource_id = 'manufacturerID'