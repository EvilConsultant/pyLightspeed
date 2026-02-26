from ..base import *
from .rseriesbase import *


class RSeriesEmployees(RSeriesApiResource, CountableApiResource):
    resource_name = 'Employee'