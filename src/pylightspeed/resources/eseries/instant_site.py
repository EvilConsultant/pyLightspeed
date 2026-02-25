from ..base import *
from .eseriesbase import *


class ESeriesInstantSite(ESeriesApiResource, ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource):
    resource_name = "startersite"
