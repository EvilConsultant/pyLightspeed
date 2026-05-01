from ..base import *
from .rseriesbase import *


class RSeriesItems(RSeriesApiResource, CreateableApiResource, UpdateableRetailApiResource, DeleteableApiResource):
    resource_name = "Item"
    resource_id = "itemID"

    # def configurable_fields(self, id=None):
    #     if id:
    #         return ProductConfigurableFields.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductConfigurableFields.all(self.id, connection=self._connection)

    # def custom_fields(self, id=None):
    #     if id:
    #         return ProductCustomFields.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductCustomFields.all(self.id, connection=self._connection)

    # def discount_rules(self, id=None):
    #     if id:
    #         return ProductDiscountRules.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductDiscountRules.all(self.id, connection=self._connection)
    def __init__(self, mapping, *args, **kwargs):
        super().__init__(mapping, *args, **kwargs)
        self._map_fields()

    def _map_fields(self):
        """Derives convenience attributes from nested Lightspeed Item data."""
        try:
            prices = self["Prices"]["ItemPrice"]
            self.price_default   = prices[0]["amount"]
            self.price_msrp      = prices[1]["amount"]
            self.price_online    = prices[2]["amount"]
            self.price_promotion = prices[3]["amount"]
        except (KeyError, IndexError, TypeError):
            pass
        try:
            self.qoh = self["ItemShops"]["ItemShop"][0]["qoh"]
        except (KeyError, IndexError, TypeError):
            self.qoh = 0

    def images(self, id=None):
        """Returns a list of images for the product based on calling the ProductImage endpoint.
        Doc here: https://developers.lightspeedhq.com/ecom/endpoints/productimage/

        Parameters
        ----------
        id : int
            The product id."""

        if id:
            return ItemImages.fetch(self.itemID, id, connection=self._connection)
        else:
            return ItemImages.all(self.itemID, connection=self._connection)

    def prices(self, id=None):
        """Returns a list of prices for the product based on calling the ProductPrice endpoint.
        Doc here: https://developers.lightspeedhq.com/ecom/endpoints/productprice/

        Parameters
        ----------
        id : int
            The product id."""

        if id:
            return ItemPrices.fetch(self.itemID, id, connection=self._connection)
        else:
            return ItemPrices.all(self.itemID, connection=self._connection)

    # def options(self, id=None):
    #     if id:
    #         return ProductOptions.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductOptions.all(self.id, connection=self._connection)

    # def reviews(self, id=None):
    #     if id:
    #         return ProductReviews.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductReviews.all(self.id, connection=self._connection)

    # def rules(self, id=None):
    #     if id:
    #         return ProductRules.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductRules.all(self.id, connection=self._connection)

    # def skus(self, id=None):
    #     if id:
    #         return ProductSkus.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductSkus.all(self.id, connection=self._connection)

    # def videos(self, id=None):
    #     if id:
    #         return ProductVideos.get(self.id, id, connection=self._connection)
    #     else:
    #         return ProductVideos.all(self.id, connection=self._connection)

    # def google_mappings(self):
    #     return GoogleProductSearchMappings.all(self.id, connection=self._connection)


# class ProductConfigurableFields(ListableApiSubResource, DeleteableApiSubResource,
#                                 CollectionDeleteableApiSubResource, CountableApiSubResource):
#     resource_name = 'configurable_fields'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/configurable_fields'


# class ProductCustomFields(ListableApiSubResource, CreateableApiSubResource,
#                           UpdateableApiSubResource, DeleteableApiSubResource,
#                           CollectionDeleteableApiSubResource, CountableApiSubResource):
#     resource_name = 'custom_fields'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/custom_fields'


# class ProductDiscountRules(ListableApiSubResource, CreateableApiSubResource,
#                            UpdateableApiSubResource, DeleteableApiSubResource,
#                            CollectionDeleteableApiSubResource, CountableApiSubResource):
#     resource_name = 'discount_rules'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/discount_rules'


class ItemImages(ListableApiSubResource):
    resource_name = "Image"
    parent_resource = "Item"
    parent_key = "itemID"


class ItemPrices(ListableApiSubResource):
    resource_name = "Prices"
    parent_resource = "Item"
    parent_key = "itemID"


# class ProductOptions(ListableApiSubResource):
#     resource_name = 'options'
#     parent_resource = 'items'
#     parent_key = 'product_id'


# class ProductReviews(ListableApiSubResource, CreateableApiSubResource,
#                    UpdateableApiSubResource, DeleteableApiSubResource,
#                    CollectionDeleteableApiSubResource, CountableApiSubResource):
#     resource_name = 'reviews'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/reviews'


# class ProductRules(ListableApiSubResource, CreateableApiSubResource,
#                    UpdateableApiSubResource, DeleteableApiSubResource,
#                    CollectionDeleteableApiSubResource, CountableApiSubResource):
#     resource_name = 'rules'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/rules'


# class ProductSkus(ListableApiSubResource, CreateableApiSubResource,
#                   UpdateableApiSubResource, DeleteableApiSubResource,
#                   CollectionDeleteableApiSubResource, CountableApiSubResource):
#     resource_name = 'skus'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/skus'


# class ProductVideos(ListableApiSubResource, CountableApiSubResource,
#                     CreateableApiSubResource, DeleteableApiSubResource,
#                     CollectionDeleteableApiSubResource):
#     resource_name = 'videos'
#     parent_resource = 'items'
#     parent_key = 'product_id'
#     count_resource = 'items/videos'


# class GoogleProductSearchMappings(ListableApiSubResource):
#     resource_name = 'googleproductsearch'
#     parent_resource = 'items'
#     parent_key = 'product_id'
