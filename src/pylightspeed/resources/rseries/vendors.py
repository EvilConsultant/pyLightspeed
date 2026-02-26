from ..base import *
from .rseriesbase import *


class RSeriesVendors(RSeriesApiResource, CreateableApiResource, UpdateableRetailApiResource, DeleteableApiResource):
    resource_name = "Vendor"
    resource_id = "vendorID"
    created_at = "timeStamp"  # Because Vendor endpoint is different from the rest of the endpoints in the R Series API
