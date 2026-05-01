# Using pyLightspeed

pyLightspeed is a wrapper for the various Lightspeed Series APIs. It simplifies accessing data across multiple series by providing a consistent interface that handles the differences between series in the background.

It was built primarily to help access and move data between R-Series and C-Series, but has been extended to include X-Series and E-Series. This allows simplified access to data and endpoints such as:

```python
from pylightspeed.api import (
    LightspeedRSeriesApi,
    LightspeedCSeriesApi,
    LightspeedXSeriesApi,
    LightspeedESeriesApi,
)

lsr = LightspeedRSeriesApi(...)
lsc = LightspeedCSeriesApi(...)
lsx = LightspeedXSeriesApi(...)
lse = LightspeedESeriesApi(...)

rseries_items    = lsr.Items.listall()
cseries_products = lsc.Products.listall()
xseries_customers = lsx.Customers.listall()
eseries_orders   = lse.Orders.listall()
```

This is based on the [BigCommerce API wrapper](https://github.com/bigcommerce/bigcommerce-api-python) because that implementation is clean and easy to use. pyLightspeed attempts to keep the same structure and feel.

## Accessing Resources

The `api` object provides access to each API resource, each of which provides CRUD operations depending on the capabilities of the resource:

```python
api.Products.page()                         # GET /products  (single page as a list)
api.Products.iterall()                      # GET /products  (autopaging generator, yields one product at a time)
api.Products.listall()                      # GET /products  (paginates through all results, returns a full list)
api.Products.get(1)                         # GET /products/1
api.Products.create(name='', type='', ...)  # POST /products
api.Products.get(1).update(price='199.90')  # PUT /products/1
api.Products.delete_all()                   # DELETE /products
api.Products.get(1).delete()                # DELETE /products/1
api.Products.count()                        # GET /products/count
```

### Subresources

Subresources are accessible as independent resources:

```python
api.ProductOptions.page(1)     # GET /products/1/options
api.ProductOptions.get(1, 2)   # GET /products/1/options/2
```

Or as helper methods on the parent resource:

```python
api.Products.get(1).variants()   # GET /products/1/variants
api.Products.get(1).variants(1)  # GET /products/1/variants/1
```

Subresources support the same CRUD methods as regular resources:

```python
api.Products.get(1).options(1).delete()
```

## Filters

Filters can be applied to `page` and `listall` methods as keyword arguments:

```python
customer = api.Customers.page(first_name='John', last_name='Smith')[0]
orders   = api.Orders.listall(customer_id=customer.id)
```

R-Series uses very specific filter formats. For complex filters, pass a raw string using the `filter` argument and refer to the [Lightspeed parameters documentation](https://developers.lightspeedhq.com/retail/introduction/parameters/).

```python
# Items with more than 24 in stock
items = lsr.Items.page(
    filter=r'load_relations=%5B%22ItemShops%22%5D&ItemShops.qoh=%3E%2C24'
)

# Recent items that have at least one image
items = lsr.Items.page(
    createTime=r'>=,2022-03-01T00:00:00-0000',
    filter=r'load_relations=%5B%22Images%22%5D&Images.imageID=%3E%2C1',
)

# Item by SKU, including images
item = lsr.Items.get(prod.sku, filter=r"load_relations=%5B%22Images%22%5D&Images.imageID=%3E%2C1")
```

!!! warning
    Lightspeed's filter syntax is very specific. Do **not** use `urllib.quote` to escape filter strings —
    it will escape `=` and `&` characters, breaking the filter without raising an error.

    Also, when using `load_relations`, if no records exist for that relation, the parent record will
    **not** be returned. This is a known limitation of the R-Series API.

## Error Handling

Minimal validation of data is performed by the client; errors are deferred to the server. An `HttpException` is raised for unusual status codes:

| Status | Exception |
|--------|-----------|
| 3xx | `RedirectionException` |
| 4xx | `ClientRequestException` |
| 5xx | `ServerException` |

## The Low-Level API

The high-level API (`pylightspeed.api.LightspeedApi`) wraps a lower-level connection in `pylightspeed.connection`, accessible via `api.connection`. It provides helper methods for `get`/`post`/`put`/`delete` operations.

## Overriding API Version Endpoints

Override the API version by passing the `version` parameter to the api object, or use the resource object to specify a path for a particular resource or call. See `resources/xseries/products.py` for an example.

## Further Documentation

- [Lightspeed R-Series API](https://developers.lightspeedhq.com/retail/introduction/introduction/)
- [Lightspeed C-Series API](https://developers.lightspeedhq.com/ecom/introduction/introduction/)
- [Lightspeed X-Series API](https://x-series-api.lightspeedhq.com/)
- [Lightspeed E-Series (Ecwid) API](https://api-docs.ecwid.com/reference/overview)
