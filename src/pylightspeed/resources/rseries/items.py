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
    def nested_json_to_attr(self):
        """Fills in the Item table with data from the Lightspeed Item object that is not automatically mapped."""
        # Lightspeed returns: 'Note': {'note': '', 'isPublic': 'false', 'timeStamp': '2022-08-24T17:30:57+00:00'},
        # obj.note=tbl.Note["note"]
        # obj.note_isPublic=tbl.Note["isPublic"]
        # obj.note_timeStamp=tbl.Note["timeStamp"]
        # Lightspeed returns: 'Prices': {'ItemPrice': [{'amount': '22.49', 'useTypeID': '1', 'useType': 'Default'}, {'amount': '22.49', 'useTypeID': '2', 'useType': 'MSRP'}, {'amount': '22.49', 'useTypeID': '3', 'useType': 'Online'}, {'amount': '22.49', 'useTypeID': '4', 'useType': 'Promotion'}]}}
        self.price_default = self["Prices"]["ItemPrice"][0]["amount"]
        self.price_msrp = self["Prices"]["ItemPrice"][1]["amount"]
        self.price_online = self["Prices"]["ItemPrice"][2]["amount"]
        self.price_promotion = self["Prices"]["ItemPrice"][3]["amount"]
        # Lightspeed returns: 'ItemShops': {'ItemShop': [{'itemShopID': '111041', 'qoh': '10', 'sellable': '10', 'backorder': '0', 'componentQoh': '0', 'componentBackorder': '0', 'reorderPoint': '0', 'reorderLevel': '0', 'timeStamp': '2022-09-01T16:37:25+00:00', 'itemID': '4564', 'shopID': '0'}, {'itemShopID': '111042', 'qoh': '10', 'sellable': '10', 'backorder': '0', 'componentQoh': '0', 'componentBackorder': '0', 'reorderPoint': '0', 'reorderLevel': '0', 'timeStamp': '2022-09-01T16:37:25+00:00', 'itemID': '4564', 'shopID': '1'}]},
        try:
            self.qoh = self["ItemShops"]["ItemShop"][0]["qoh"]
        except:
            self.qoh = 0

    def images(self, id=None):
        """Returns a list of images for the product based on calling the ProductImage endpoint.
        Doc here: https://developers.lightspeedhq.com/ecom/endpoints/productimage/

        Parameters
        ----------
        id : int
            The product id."""

        if id:
            return ItemImages.get(self.itemID, id, connection=self._connection)
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
            return ItemPrices.get(self.itemID, id, connection=self._connection)
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
