from ..base import *


class RSeriesCategories(ListableRetailApiResource, UpdateableRetailApiResource, CreateableApiResource, CountableApiResource):
    """LS Retail Categories API Resource. https://developers.lightspeedhq.com/retail/endpoints/Category/"""
    resource_name = 'Category'
    resource_id = 'categoryID'

# I started with this but I think it is for the ecom api
# class Categories(ListableApiResource, CountableApiResource):
#     resource_name = 'categories'