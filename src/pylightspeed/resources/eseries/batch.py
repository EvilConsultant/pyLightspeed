from ..base import *
from .eseriesbase import *


class ESeriesBatch(ESeriesApiResource, ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource):
    resource_name = "batch"
