# https://x-series-api.lightspeedhq.com/reference/listtags
# DONT FORGET TO ADD TO __init__.py

from ..base import *
from .xseriesbase import *


class XSeriesTags(
    XSeriesApiResource,
    ListableApiResource,
    CreateableApiResource,
    UpdateableApiResource,
    DeleteableApiResource,
    CountableApiResource,
):
    resource_name = "tags"
