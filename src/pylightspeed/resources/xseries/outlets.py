from ..base import *
from .xseriesbase import *


class XSeriesOutlets(
    XSeriesApiResource,
    ListableApiResource,
):
    resource_name = "outlets"
