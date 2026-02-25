from ..base import *


class CSeriesSubscriptions(ListableApiResource, UpdateableApiResource, CreateableApiResource, CountableApiResource):
    """LS Ecom suubscriptions API Resource. https://developers.lightspeedhq.com/ecom/endpoints/subscription/"""
    resource_name = 'subscriptions'