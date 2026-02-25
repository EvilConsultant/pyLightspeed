from ..base import *
from .eseriesbase import *


class ESeriesOrders(ESeriesApiResource, ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource):
    resource_name = "orders"
