## R-Series Item List Payload Example

{
  "@attributes": {
    "next": "",
    "previous": ""
  },
  "Item": [
    {
      "itemID": "20",
      "systemSku": "210000000020",
      "defaultCost": "0",
      "avgCost": "100",
      "discountable": "true",
      "tax": "true",
      "archived": "false",
      "itemType": "default",
      "serialized": "false",
      "description": "Matrix",
      "modelYear": "0",
      "upc": "",
      "ean": "",
      "customSku": "matrix",
      "manufacturerSku": "",
      "createTime": "2021-06-27T13:15:25+00:00",
      "timeStamp": "2021-03-03T13:51:56+00:00",
      "publishToEcom": "true",
      "categoryID": "0",
      "taxClassID": "1",
      "departmentID": "0",
      "itemMatrixID": "0",
      "manufacturerID": "0",
      "seasonID": "0",
      "defaultVendorID": "0",
      "Prices": {
        "ItemPrice": [
          {
            "amount": "100",
            "useTypeID": "1",
            "useType": "Default"
          },
          {
            "amount": "0",
            "useTypeID": "2",
            "useType": "MSRP"
          },
          {
            "amount": "0",
            "useTypeID": "3",
            "useType": "Online"
          }
        ]
      }
    },
    {...}
  ]
}

## C-Series Product Payload Example

{
    "product": {
        "id": 20967267,
        "createdAt": "2019-05-28T15:25:46+00:00",
        "updatedAt": "2019-05-28T17:16:16+00:00",
        "isVisible": true,
        "visibility": "visible",
        "hasMatrix": false,
        "data01": "",
        "data02": "",
        "data03": "",
        "url": "lookin-sharp-tee",
        "title": "Lookin' Sharp T-Shirt",
        "fulltitle": "Lookin' Sharp T-Shirt",
        "description": "Description of the Lookin' Sharp T-Shirt",
        "content": "<p>Long Description of the Lookin' Sharp T-Shirt</p>",
        "set": {
            "id": 2785,
            "createdAt": "2019-05-28T15:32:12+00:00",
            "updatedAt": "2019-05-28T15:42:59+00:00",
            "name": "Shirts",
            "options": [
                {
                    "id": 4626,
                    "sortOrder": 1,
                    "name": "Size",
                    "values": [
                        {
                            "id": 14045,
                            "sortOrder": 1,
                            "name": "S"
                        },
                        {
                            "id": 14046,
                            "sortOrder": 2,
                            "name": "M"
                        },
                        {
                            "id": 14047,
                            "sortOrder": 3,
                            "name": "L"
                        }
                    ]
                }
            ]
        },
        "brand": {
            "resource": {
                "id": 1171202,
                "url": "brands/1171202",
                "link": "https://api.shoplightspeed.com/us/brands/1171202.json"
            }
        },
        "categories": {
            "resource": {
                "id": false,
                "url": "categories/products?product=20967267",
                "link": "https://api.shoplightspeed.com/us/categories/products.json?product=20967267"
            }
        },
        "deliverydate": {
            "resource": {
                "id": 6488,
                "url": "deliverydates/6488",
                "link": "https://api.shoplightspeed.com/us/deliverydates/6488.json"
            }
        },
        "image": {
            "createdAt": "2019-05-28T15:25:46+00:00",
            "updatedAt": "2019-05-28T15:25:46+00:00",
            "extension": "jpg",
            "size": 86649,
            "title": "17x35x-jcfk-88na-udwd-5hck-z63u-img-16-e0aa4f57-f4",
            "thumb": "https://cdn.shoplightspeed.com/shops/000001/files/14119398/50x50x2/17x35x-jcfk-88na-udwd-5hck-z63u-img-16-e0aa4f57-f4.jpg",
            "src": "https://cdn.shoplightspeed.com/shops/000001/files/14119398/17x35x-jcfk-88na-udwd-5hck-z63u-img-16-e0aa4f57-f4.jpg"
        },
        "images": {
            "resource": {
                "id": false,
                "url": "products/20967267/images",
                "link": "https://api.shoplightspeed.com/us/products/20967267/images.json"
            }
        },
        "relations": {
            "resource": {
                "id": false,
                "url": "products/20967267/relations",
                "link": "https://api.shoplightspeed.com/us/products/20967267/relations.json"
            }
        },
        "metafields": {
            "resource": {
                "id": false,
                "url": "products/20967267/metafields",
                "link": "https://api.shoplightspeed.com/us/products/20967267/metafields.json"
            }
        },
        "reviews": {
            "resource": {
                "id": false,
                "url": "reviews?product=20967267",
                "link": "https://api.shoplightspeed.com/us/reviews.json?product=20967267"
            }
        },
        "type": false,
        "attributes": {
            "resource": {
                "id": false,
                "url": "products/20967267/attributes",
                "link": "https://api.shoplightspeed.com/us/products/20967267/attributes.json"
            }
        },
        "supplier": {
            "resource": {
                "id": 78794,
                "url": "suppliers/78794",
                "link": "https://api.shoplightspeed.com/us/suppliers/78794.json"
            }
        },
        "tags": {
            "resource": {
                "id": false,
                "url": "tags/products?product=20967267",
                "link": "https://api.shoplightspeed.com/us/tags/products.json?product=20967267"
            }
        },
        "variants": {
            "resource": {
                "id": false,
                "url": "variants?product=20967267",
                "link": "https://api.shoplightspeed.com/us/variants.json?product=20967267"
            }
        },
        "movements": {
            "resource": {
                "id": false,
                "url": "variants/movements?product=20967267",
                "link": "https://api.shoplightspeed.com/us/variants/movements.json?product=20967267"
            }
        },
        "templateDataFields": {
            "data01": "Template Data Field 1",
            "data02": "Template Data Field 2",
            "data03": "Template Data Field 3",
            "data04": "Template Data Field 4"
        }
    }
}

##C-Series Variant Payload Example
{
    "variant": {
        "id": 36285796,
        "createdAt": "2019-07-24T15:23:06+00:00",
        "updatedAt": "2019-08-01T16:10:58+00:00",
        "isDefault": true,
        "sortOrder": 1,
        "articleCode": "",
        "ean": "",
        "sku": "",
        "hs": "",
        "unitPrice": 0,
        "unitUnit": null,
        "priceExcl": 0,
        "priceIncl": 0,
        "priceCost": 0,
        "oldPriceExcl": 23,
        "oldPriceIncl": 23,
        "stockTracking": "indicator",
        "stockLevel": 100,
        "stockAlert": 5,
        "stockMinimum": 0,
        "stockSold": 0,
        "stockBuyMininum": 1,
        "stockBuyMinimum": 1,
        "stockBuyMaximum": 10000,
        "weight": 0,
        "weightValue": "0.000",
        "weightUnit": "lb",
        "volume": 0,
        "volumeValue": 0,
        "volumeUnit": "fl_oz",
        "colli": 0,
        "sizeX": 0,
        "sizeY": 0,
        "sizeZ": 0,
        "sizeXValue": "0.000",
        "sizeYValue": "0.000",
        "sizeZValue": "0.000",
        "sizeUnit": "in",
        "matrix": false,
        "title": "Default",
        "taxType": "auto",
        "image": {
            "createdAt": "2019-08-01T16:10:27+00:00",
            "updatedAt": "2019-08-01T16:10:27+00:00",
            "extension": "png",
            "size": 8016,
            "title": "logo",
            "thumb": "https://cdn.shoplightspeed.com/shops/111111/files/15142984/50x50x2/logo.png",
            "src": "https://cdn.shoplightspeed.com/shops/111111/files/15142984/logo.png"
        },
        "tax": false,
        "product": {
            "resource": {
                "id": 21881217,
                "url": "products/21881217",
                "link": "https://api.shoplightspeed.com/us/products/21881217.json"
            }
        },
        "movements": {
            "resource": {
                "id": false,
                "url": "variants/movements?variant=36285796",
                "link": "https://api.shoplightspeed.com/us/variants/movements.json?variant=36285796"
            }
        },
        "metafields": {
            "resource": {
                "id": false,
                "url": "variants/36285796/metafields",
                "link": "https://api.shoplightspeed.com/us/variants/36285796/metafields.json"
            }
        },
        "additionalcost": false,
        "options": []
    }
}


## X-Series List Product Payload Example

{
  "data": [
    {
      "id": "b8ca3a65-0183-11e4-fbb5-9776c5cd0240",
      "name": "Product 0003",
      "variant_name": "Product 0003",
      "handle": "0003",
      "sku": "0003",
      "active": true,
      "has_inventory": true,
      "is_composite": false,
      "image_url": "https://secure.retail.lightspeed.app/images/placeholder/product/no-image-white-standard.png",
      "created_at": "2015-01-08T20:41:50+00:00",
      "updated_at": "2015-08-18T23:28:00+00:00",
      "source": "USER",
      "supply_price": 0,
      "version": 59780745,
      "type": {},
      "supplier": {},
      "brand": {},
      "variant_options": [],
      "categories": [],
      "images": [],
      "has_variants": false,
      "button_order": 0,
      "price_including_tax": 3.02632,
      "price_excluding_tax": 2.63158,
      "is_active": true,
      "image_thumbnail_url": "https://secure.retail.lightspeed.app/images/placeholder/product/no-image-white-thumb.png",
      "tag_ids": [],
      "attributes": []
    },
    {
      "id": "b8ca3a65-0183-11e4-fbb5-9776c5faaed2",
      "name": "Product 0005",
      "variant_name": "Product 0005",
      "handle": "0005",
      "sku": "0005",
      "active": true,
      "has_inventory": true,
      "is_composite": false,
      "image_url": "https://secure.retail.lightspeed.app/images/placeholder/product/no-image-white-standard.png",
      "created_at": "2015-01-08T20:41:51+00:00",
      "updated_at": "2015-08-18T23:28:00+00:00",
      "source": "USER",
      "supply_price": 0,
      "version": 59780753,
      "type": {},
      "supplier": {},
      "brand": {},
      "variant_options": [],
      "categories": [],
      "images": [],
      "has_variants": false,
      "button_order": 0,
      "price_including_tax": 5.04385,
      "price_excluding_tax": 4.38596,
      "is_active": true,
      "image_thumbnail_url": "https://secure.retail.lightspeed.app/images/placeholder/product/no-image-white-thumb.png",
      "tag_ids": [],
      "attributes": []
    },
    {
      "id": "b8ca3a65-0183-11e4-fbb5-9776c611d865",
      "name": "Product 0006",
      "variant_name": "Product 0006",
      "handle": "0006",
      "sku": "0006",
      "active": true,
      "has_inventory": true,
      "is_composite": false,
      "image_url": "https://secure.retail.lightspeed.app/images/placeholder/product/no-image-white-standard.png",
      "created_at": "2015-01-08T20:41:51+00:00",
      "updated_at": "2015-08-18T23:28:00+00:00",
      "source": "USER",
      "supply_price": 0,
      "version": 59780757,
      "type": {},
      "supplier": {},
      "brand": {},
      "variant_options": [],
      "categories": [],
      "images": [],
      "has_variants": false,
      "button_order": 0,
      "price_including_tax": 6.05263,
      "price_excluding_tax": 5.26316,
      "is_active": true,
      "image_thumbnail_url": "https://secure.retail.lightspeed.app/images/placeholder/product/no-image-white-thumb.png",
      "tag_ids": [],
      "attributes": [],
      "product_codes": [
        {
          "type": "custom",
          "code": "123456"
        }
      ],
      "product_suppliers": [
        {
          "id": "cfbf30bd-4b6a-47df-931c-1a326acc1769",
          "product_id": "d796d8b2-ff79-48fa-8e6e-a15e2e0bd429",
          "supplier_id": "63c4c033-3019-4582-99e7-446baacca1b0",
          "supplier_name": "supplier_1",
          "code": "code",
          "price": 19
        }
      ]
    }
  ],
  "version": {
    "min": 59780745,
    "max": 59780757
  }
}

## E-Series Get Product Example

{
  "id": 692730761,
  "sku": "123123",
  "thumbnailUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591923.jpg",
  "unlimited": true,
  "inStock": true,
  "name": "Toys",
  "nameTranslated": {
    "cs": "",
    "en": "Toys"
  },
  "price": 10,
  "priceInProductList": 10,
  "defaultDisplayedPrice": 10,
  "defaultDisplayedPriceFormatted": "€10,00",
  "tax": {
    "taxable": true,
    "defaultLocationIncludedTaxRate": 10,
    "enabledManualTaxes": [
      947976181
    ],
    "taxClassCode": "default"
  },
  "lowestPrice": 10,
  "defaultDisplayedLowestPrice": 10,
  "defaultDisplayedLowestPriceFormatted": "€10,00",
  "lowestPriceSettings": {
    "lowestPriceEnabled": true
  },
  "isShippingRequired": false,
  "hasFreeShipping": false,
  "url": "https://store1003.company.site/products/toys-692730761",
  "autogeneratedSlug": "toys-692730761",
  "customSlug": "",
  "created": "2024-09-04 07:20:11 +0000",
  "updated": "2024-09-04 07:20:12 +0000",
  "createTimestamp": 1725434411,
  "updateTimestamp": 1725434412,
  "productClassId": 0,
  "enabled": true,
  "options": [],
  "warningLimit": 1,
  "fixedShippingRateOnly": false,
  "fixedShippingRate": 0,
  "shipping": {
    "type": "GLOBAL_METHODS",
    "methodMarkup": 0,
    "flatRate": 0,
    "disabledMethods": [],
    "enabledMethods": []
  },
  "defaultCombinationId": 0,
  "imageUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591921.jpg",
  "smallThumbnailUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591920.jpg",
  "hdThumbnailUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591922.jpg",
  "originalImageUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591919.jpg",
  "originalImage": {
    "url": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591919.jpg",
    "width": 225,
    "height": 225
  },
  "borderInfo": {
    "dominatingColor": {
      "red": 255,
      "green": 255,
      "blue": 255,
      "alpha": 255
    },
    "homogeneity": true
  },
  "description": "",
  "descriptionTranslated": {
    "cs": "",
    "en": ""
  },
  "galleryImages": [],
  "media": {
    "images": [
      {
        "id": "0",
        "isMain": true,
        "orderBy": 0,
        "image160pxUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591920.jpg",
        "image400pxUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591923.jpg",
        "image800pxUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591922.jpg",
        "image1500pxUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591921.jpg",
        "imageOriginalUrl": "https://d2j6dbq0eux0bg.cloudfront.net/images/1003/4519591919.jpg",
        "alt": {
          "translated": {}
        }
      }
    ],
    "videos": []
  },
  "categoryIds": [],
  "categories": [],
  "defaultCategoryId": 0,
  "seoTitle": "Toys",
  "seoTitleTranslated": {
    "cs": "",
    "en": "Toys"
  },
  "seoDescription": "",
  "seoDescriptionTranslated": {
    "cs": "",
    "en": ""
  },
  "favorites": {
    "count": 0,
    "displayedCount": "0"
  },
  "attributes": [],
  "files": [
    {
      "id": 96178524,
      "name": "image.jpeg",
      "description": "",
      "size": 12006,
      "adminUrl": "https://app.ecwid.com/api/v3/1003/products/692730761/files/96178524"
    }
  ],
  "relatedProducts": {
    "productIds": [],
    "relatedCategory": {
      "enabled": false,
      "categoryId": 0,
      "productCount": 5
    }
  },
  "combinations": [],
  "dimensions": {
    "length": 0,
    "width": 0,
    "height": 0
  },
  "shippingPreparationTime": {},
  "showDeliveryTimeInStorefront": false,
  "volume": 0,
  "showOnFrontpage": 11,
  "isSampleProduct": false,
  "googleItemCondition": "NEW",
  "isGiftCard": false,
  "discountsAllowed": true,
  "nameYourPriceEnabled": false,
  "subscriptionSettings": {
    "subscriptionAllowed": false,
    "oneTimePurchaseAllowed": true,
    "recurringChargeSettings": [
      {
        "recurringInterval": "MONTH",
        "recurringIntervalCount": 1
      }
    ]
  },
  "googleProductCategory": 412,
  "googleProductCategoryName": "Food, Beverages & Tobacco",
  "productCondition": "NEW",
  "outOfStockVisibilityBehaviour": "SHOW"
}