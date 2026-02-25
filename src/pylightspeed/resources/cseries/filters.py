from ..base import *


class CSeriesFilters(ListableApiResource, CountableApiResource):
    """LS C-Series API Resource. https://developers.lightspeedhq.com/ecom/endpoints/filter/"""

    resource_name = "filters"


class CSeriesFilterValues(ListableApiSubResource, CountableApiSubResource):
    """LS C-Series API Resource. https://developers.lightspeedhq.com/ecom/endpoints/filtervalue/"""

    resource_name = "values"
    parent_resource = "filters"
    parent_key = "filter_id"
    count_resource = "filters/{}/values"
