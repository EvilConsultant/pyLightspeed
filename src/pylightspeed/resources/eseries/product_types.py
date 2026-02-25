from ..base import *
from .eseriesbase import *


class ESeriesProductTypes(ESeriesApiResource, ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource):
    resource_name = "classes"
