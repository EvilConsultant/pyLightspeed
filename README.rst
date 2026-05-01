pyLightspeed 
------------
Lightspeed API Python Client


This is a python wrapper for the Lightspeed API. It is based on the Bigcommerce API wrapper because I found that 
it offered a lot of the functionality needed and was implemented well. Since I use both, I wanted this one to 
be very similar, so it is. And I thought pyLightspeed was a pun on PoliteSpeed.


Usage
-----



Accessing and objects
~~~~~~~~~~~~~~~~~~~~~

The ``api`` object provides access to each API resource, each of which
provides CRUD operations, depending on capabilities of the resource:

.. code:: python

    api.Products.page()                         # GET /products (returns only a single page of products as a list)
    api.Products.iterall()                     # GET /products (autopaging generator that yields all
                                               #                  products from all pages product by product.)
    api.Products.listall()                          # GET /products (paginates through the total results and returns a list of all products)
    api.Products.get(1)                        # GET /products/1
    api.Products.create(name='', type='', ...) # POST /products
    api.Products.get(1).update(price='199.90') # PUT /products/1
    api.Products.delete_all()                  # DELETE /products
    api.Products.get(1).delete()               # DELETE /products/1
    api.Products.count()                       # GET /products/count

The client provides full access to subresources, both as independent
resources:

.. code:: python

    api.ProductOptions.page(1)                  # GET /products/1/options - note that get doesn't work with only 1
    api.ProductOptions.get(1, 2)               # GET /products/1/options/2

And as helper methods on the parent resource:

.. code:: python
    #maybe not implemented yet
    api.Products.get(1).variants()              # GET /products/1/variants
    api.Products.get(1).variants(1)             # GET /products/1/variants/1

These subresources implement CRUD methods in exactly the same way as
regular resources:

.. code:: python

    api.Products.get(1).options(1).delete()

Filters
~~~~~~~

Filters can be applied to ``page`` and ``listall`` methods as keyword arguments:

.. code:: python

    customer = api.Customers.page(first_name='John', last_name='Smith')[0]
    orders = api.Orders.listall(customer_id=customer.id)

However, Lightspeed R-Series more complicated filters have very specific formats which are not easy to 
manage with something simple like wrllib.quote, so you can also pass a raw string using the filter argument.
Reference the https://developers.lightspeedhq.com/retail/introduction/parameters/ for the specific formats LS requires.

.. code:: python
    # Find items with more than 24 items in stock
    items = lsretail.Items.page(filter = r'load_relations=%5B%22ItemShops%22%5D&ItemShops.qoh=%3E%2C24')
    # Find all recent items with an image (by loading images, and returining imageID>1)
    # In this example, the parameter for createTime includes the LS operator which will be URL escaped, and the filter parameter which will be used raw.
    items = lsretail.Items.page(createTime=r'>=,2022-03-01T00:00:00-0000', filter = r'load_relations=%5B%22Images%22%5D&Images.imageID=%3E%2C1')

    #Get an item with a specific SKU and load images
    item = lsr.Items.get(prod.sku, filter=r"load_relations=%5B%22Images%22%5D&Images.imageID=%3E%2C1")
Remember Lightspeed's filter syntax is very specific, so you may need to use the filter argument instead of the keyword arguments.
You will need to correctly escape the filter string manually. Be aware that if you use urllib.quote it will escape the = and & characters, which will cause the filter to not work but likely won't throw an error.

Also, if you are using load_relations and their are no records for that relation, no records will be returned. For example, in the above
example, if there are no images for the item, the item will not be returned. This is a limitation of the Lightspeed R-Series API.

Error handling
~~~~~~~~~~~~~~

Minimal validation of data is performed by the client, instead deferring
this to the server. A ``HttpException`` will be raised for any unusual
status code:

-  3xx status code: ``RedirectionException``
-  4xx status code: ``ClientRequestException``
-  5xx status code: ``ServerException``

The low level API
~~~~~~~~~~~~~~~~~

The high level API provided by ``pylightspeed.api.LightspeedApi`` is a
wrapper around a lower level api in ``pylightspeed.connection``. This can
be accessed through ``api.connection``, and provides helper methods for
get/post/put/delete operations.

Accessing Different API Version endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~
Override the api version by passing the version parameter to the api object, or use the resource object to access a specific version.
See resources/xseries/products.update_path() for an example of how to override the path for a specific resource, or specific call (get, post, put, delete) for a resource.


To do
-----

-  Oh jeez, so much.

