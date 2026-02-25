from ..base import *
from .rseriesbase import *


class RSeriesImages(RSeriesApiResource, ListableRetailApiResource, UpdateableRetailApiResource, CreateableApiResource, DeleteableRSeriesApiResource):
    """LS Retail Image API Resource. https://developers.lightspeedhq.com/retail/endpoints/Image/"""

    resource_name = "Image"
    resource_id = "imageID"
