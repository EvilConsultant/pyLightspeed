# XSeries: Products Endpoint
# https://docs.vendhq.com/reference/listproducts-2

# QUERY PARAMS
# after
# int64
# The lower limit for the version numbers to be included in the response.

# before
# int64
# The upper limit for the version numbers to be included in the response.

# deleted
# boolean
# Indicates whether deleted items should be included in the response.


# page_size
# integer
# The maximum number of items to be returned in the response.

from ..base import *
from .xseriesbase import *

import requests


class XSeriesProducts(
    XSeriesApiResource,
    ListableApiResource,
    CreateableApiResource,
    UpdateableApiResource,
    DeleteableApiResource,
    CollectionDeleteableApiResource,
    CountableApiResource,
):
    resource_name = "products"
    to_rseries_mapping = {"name": "name"}

    def _update_path(self):
        return "api/2.1/products/{}".format(self.id)


class XSeriesProducts9(
    XSeriesApiResource,
    ListableApiResource,
    CreateableApiResource,
    UpdateableApiResource,
    DeleteableApiResource,
    CollectionDeleteableApiResource,
    CountableApiResource,
):
    resource_name = "products"
    to_rseries_mapping = {"name": "name"}

    def _update_path(self):
        return "api/products"


class XSeriesProduct_Images(ListableApiSubResource, CreateableApiSubResource):
    resource_name = "actions/image_upload"
    parent_resource = "products"
    parent_key = "id"


example = {
    "id": "48f3662a-c514-4994-8ebc-610526034712",
    "source_id": None,
    "source_variant_id": None,
    "variant_parent_id": None,
    "name": "19 Crimes Chardonnay 'Martha's Chard' (2021)",
    "variant_name": "19 Crimes Chardonnay 'Martha's Chard' (2021)",
    "handle": "19-crimes-chardonnay-marthas-chard-2021",
    "sku": "012354007437",
    "supplier_code": None,
    "active": True,
    "ecwid_enabled_webstore": False,
    "has_inventory": True,
    "is_composite": False,
    "description": "<p>19 Crimes tells the true story of heroes who beat the odds and overcame adversity to become folk heroes. This spirit lives on today through innovators like Martha Stewart, a self-made icon who built a domestic empire. Martha’s drive embodies the timeless values of the 19 Crimes mavericks who came before her.</p>\n<h2>Tasting Notes</h2>\n<p>91 Wine Enthusiast<br />A deft touch with oak gives this medium- to full-bodied wine spicy complexity. It ranges from a toasted baguette aroma to light butter and ginger flavors over golden apple and Bosc pear. Best Buy</p>",
    "image_url": "https://vendimageuploadcdn.global.ssl.fastly.net/350,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
    "deleted_at": None,
    "source": "RSERIES",
    "account_code": None,
    "account_code_purchase": None,
    "supply_price": 1.0,
    "version": 35319095545,
    "type": {"id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab", "name": "$99 Case", "deleted_at": None, "version": 35186403951},
    "product_category": {
        "id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab",
        "name": "$99 Case",
        "leaf_category": True,
        "category_path": [{"id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab", "name": "$99 Case"}],
    },
    "supplier": {
        "id": "60851cbb-9329-4de6-a24a-b706b6c248d0",
        "name": "Breakthru Beverage",
        "source": "USER",
        "description": "700103225",
        "deleted_at": None,
        "version": 35182354943,
    },
    "brand": None,
    "variant_options": [],
    "categories": [],
    "images": [
        {
            "id": "d63f92fa-9cec-4bff-b6d4-afa9c877aea9",
            "url": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
            "version": 35230363782,
            "sizes": {
                "raw": "https://vendimageuploadcdn.global.ssl.fastly.net/0x0/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "original": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "sl": "https://vendimageuploadcdn.global.ssl.fastly.net/150x150,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "sm": "https://vendimageuploadcdn.global.ssl.fastly.net/100x100,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "ss": "https://vendimageuploadcdn.global.ssl.fastly.net/50x50,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "st": "https://vendimageuploadcdn.global.ssl.fastly.net/40x40,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "standard": "https://vendimageuploadcdn.global.ssl.fastly.net/350,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "thumb": "https://vendimageuploadcdn.global.ssl.fastly.net/160,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
            },
        },
        {
            "id": "b035c659-1524-49e0-beeb-159bba2c844d",
            "url": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
            "version": 35230363783,
            "sizes": {
                "raw": "https://vendimageuploadcdn.global.ssl.fastly.net/0x0/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "original": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "sl": "https://vendimageuploadcdn.global.ssl.fastly.net/150x150,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "sm": "https://vendimageuploadcdn.global.ssl.fastly.net/100x100,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "ss": "https://vendimageuploadcdn.global.ssl.fastly.net/50x50,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "st": "https://vendimageuploadcdn.global.ssl.fastly.net/40x40,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "standard": "https://vendimageuploadcdn.global.ssl.fastly.net/350,fit,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "thumb": "https://vendimageuploadcdn.global.ssl.fastly.net/160,fit,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
            },
        },
    ],
    "skuImages": [],
    "has_variants": False,
    "variant_count": None,
    "button_order": 0,
    "price_including_tax": 9.99,
    "price_excluding_tax": 9.99,
    "loyalty_amount": None,
    "product_codes": [
        {"id": "202fe086-0b0f-4fab-9d06-853bf27184af", "type": "CUSTOM", "code": "210000006355"},
        {"id": "e5e48db5-100e-4f7a-b534-a7a7fcbbacc9", "type": "UPC", "code": "012354007437"},
    ],
    "product_suppliers": [
        {
            "id": "d859867a-f06a-4f14-a24f-20ba7acefe24",
            "product_id": "48f3662a-c514-4994-8ebc-610526034712",
            "supplier_id": "60851cbb-9329-4de6-a24a-b706b6c248d0",
            "supplier_name": "Breakthru Beverage",
            "code": None,
            "price": 1.0,
        }
    ],
    "packaging": {"made_from": [], "breaks_into": []},
    "weight": 1360.0,
    "weight_unit": "G",
    "length": 10.0,
    "width": 10.0,
    "height": 30.0,
    "dimensions_unit": "CM",
    "attributes": [],
    "supplier_id": "60851cbb-9329-4de6-a24a-b706b6c248d0",
    "is_active": True,
    "image_thumbnail_url": "https://vendimageuploadcdn.global.ssl.fastly.net/160,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
    "product_type_id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab",
    "brand_id": None,
    "tag_ids": [],
    "json": {
        "id": "48f3662a-c514-4994-8ebc-610526034712",
        "source_id": None,
        "source_variant_id": None,
        "variant_parent_id": None,
        "name": "19 Crimes Chardonnay 'Martha's Chard' (2021)",
        "variant_name": "19 Crimes Chardonnay 'Martha's Chard' (2021)",
        "handle": "19-crimes-chardonnay-marthas-chard-2021",
        "sku": "012354007437",
        "supplier_code": None,
        "active": True,
        "ecwid_enabled_webstore": False,
        "has_inventory": True,
        "is_composite": False,
        "description": "<p>19 Crimes tells the true story of heroes who beat the odds and overcame adversity to become folk heroes. This spirit lives on today through innovators like Martha Stewart, a self-made icon who built a domestic empire. Martha’s drive embodies the timeless values of the 19 Crimes mavericks who came before her.</p>\n<h2>Tasting Notes</h2>\n<p>91 Wine Enthusiast<br />A deft touch with oak gives this medium- to full-bodied wine spicy complexity. It ranges from a toasted baguette aroma to light butter and ginger flavors over golden apple and Bosc pear. Best Buy</p>",
        "image_url": "https://vendimageuploadcdn.global.ssl.fastly.net/350,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
        "created_at": "2024-04-03T16:12:29+00:00",
        "updated_at": "2024-04-08T20:21:22+00:00",
        "deleted_at": None,
        "source": "RSERIES",
        "account_code": None,
        "account_code_purchase": None,
        "supply_price": 1.0,
        "version": 35319095545,
        "type": {"id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab", "name": "$99 Case", "deleted_at": None, "version": 35186403951},
        "product_category": {
            "id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab",
            "name": "$99 Case",
            "leaf_category": True,
            "category_path": [{"id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab", "name": "$99 Case"}],
        },
        "supplier": {
            "id": "60851cbb-9329-4de6-a24a-b706b6c248d0",
            "name": "Breakthru Beverage",
            "source": "USER",
            "description": "700103225",
            "deleted_at": None,
            "version": 35182354943,
        },
        "brand": None,
        "variant_options": [],
        "categories": [],
        "images": [
            {
                "id": "d63f92fa-9cec-4bff-b6d4-afa9c877aea9",
                "url": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                "version": 35230363782,
                "sizes": {
                    "raw": "https://vendimageuploadcdn.global.ssl.fastly.net/0x0/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "original": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "sl": "https://vendimageuploadcdn.global.ssl.fastly.net/150x150,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "sm": "https://vendimageuploadcdn.global.ssl.fastly.net/100x100,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "ss": "https://vendimageuploadcdn.global.ssl.fastly.net/50x50,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "st": "https://vendimageuploadcdn.global.ssl.fastly.net/40x40,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "standard": "https://vendimageuploadcdn.global.ssl.fastly.net/350,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                    "thumb": "https://vendimageuploadcdn.global.ssl.fastly.net/160,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
                },
            },
            {
                "id": "b035c659-1524-49e0-beeb-159bba2c844d",
                "url": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                "version": 35230363783,
                "sizes": {
                    "raw": "https://vendimageuploadcdn.global.ssl.fastly.net/0x0/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "original": "https://vendimageuploadcdn.global.ssl.fastly.net/1920,fit/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "sl": "https://vendimageuploadcdn.global.ssl.fastly.net/150x150,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "sm": "https://vendimageuploadcdn.global.ssl.fastly.net/100x100,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "ss": "https://vendimageuploadcdn.global.ssl.fastly.net/50x50,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "st": "https://vendimageuploadcdn.global.ssl.fastly.net/40x40,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "standard": "https://vendimageuploadcdn.global.ssl.fastly.net/350,fit,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                    "thumb": "https://vendimageuploadcdn.global.ssl.fastly.net/160,fit,q90/vend-images/product/original/5d17bfeef374dcfc703307ce4d91e8284be19c9d/efyz3xyznogx9wkazvrf.jpg",
                },
            },
        ],
        "skuImages": [],
        "has_variants": False,
        "variant_count": None,
        "button_order": 0,
        "price_including_tax": 9.99,
        "price_excluding_tax": 9.99,
        "loyalty_amount": None,
        "product_codes": [
            {"id": "202fe086-0b0f-4fab-9d06-853bf27184af", "type": "CUSTOM", "code": "210000006355"},
            {"id": "e5e48db5-100e-4f7a-b534-a7a7fcbbacc9", "type": "UPC", "code": "012354007437"},
        ],
        "product_suppliers": [
            {
                "id": "d859867a-f06a-4f14-a24f-20ba7acefe24",
                "product_id": "48f3662a-c514-4994-8ebc-610526034712",
                "supplier_id": "60851cbb-9329-4de6-a24a-b706b6c248d0",
                "supplier_name": "Breakthru Beverage",
                "code": None,
                "price": 1.0,
            }
        ],
        "packaging": {"made_from": [], "breaks_into": []},
        "weight": 1360.0,
        "weight_unit": "G",
        "length": 10.0,
        "width": 10.0,
        "height": 30.0,
        "dimensions_unit": "CM",
        "attributes": [],
        "supplier_id": "60851cbb-9329-4de6-a24a-b706b6c248d0",
        "is_active": True,
        "image_thumbnail_url": "https://vendimageuploadcdn.global.ssl.fastly.net/160,fit,q90/vend-images/product/original/26a8f006fa40ca91dd2ee2c3889f248a00e3a4d3/magq2wcez0dilbayeh09.jpg",
        "product_type_id": "c8926c50-9ee7-49f4-8f8a-81afe7f4adab",
        "brand_id": None,
        "tag_ids": [],
    },
}
