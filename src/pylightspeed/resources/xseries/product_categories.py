# https://docs.vendhq.com/reference/

from ..base import *
from .xseriesbase import *

# Response sample:
example = (
    {
        "id": "cbab3091-9a35-4009-bdbf-9b881538996e",
        "name": "United States",
        "leaf_category": False,
        "category_path": [{"id": "cbab3091-9a35-4009-bdbf-9b881538996e", "name": "United States"}],
        "deleted_at": None,
        "version": 30274264811,
    },
)
{
    "id": "a4b588a1-ba7a-4bdd-9f5e-6491e3cce0cd",
    "name": "Missouri",
    "leaf_category": True,
    "category_path": [
        {"id": "cbab3091-9a35-4009-bdbf-9b881538996e", "name": "United States"},
        {"id": "a4b588a1-ba7a-4bdd-9f5e-6491e3cce0cd", "name": "Missouri"},
    ],
    "deleted_at": None,
    "version": 30274264812,
}


class XSeriesProductCategories(XSeriesApiResource, ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource):
    # api_path = "/api/{}"
    resource_name = "product_categories"

    # This is changing to product_categories in the new API, so be ready
