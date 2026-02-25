# https://docs.vendhq.com/reference/listbrands

from ..base import *
from .xseriesbase import *

example = {
  "data": [
    {
      "id": "0adaafb3-6583-11e5-fb60-d5b67a17df2f",
      "name": "Peak Performance",
      "version": 882391722
    },
    {
      "id": "0adaafb3-6583-11e5-fb60-ebae84675ae4",
      "name": "Sennheiser",
      "version": 1013841198
    },
    {
      "id": "b1e2624f-f019-11e3-a0f5-b8ca3a64f8f4",
      "name": "Generic Brand",
      "version": 2364279587
    }
  ]
}

class XSeriesBrands(XSeriesApiResource, ListableApiResource, CreateableApiResource,
               UpdateableApiResource, DeleteableApiResource,
               CollectionDeleteableApiResource, CountableApiResource):
    resource_name = 'brands'
    to_rseries_mapping = {'name': 'name'}