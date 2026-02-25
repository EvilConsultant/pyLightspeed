Connecting to Lightspeed's APIs
====================

This is a python wrapper for the Lightspeed API. It is based on the Bigcommerce API wrapper because I found that 
it offered a lot of the functionality needed and was implemented well. Since I use both, I wanted this one to 
be very similar, so it is. And I thought pyLightspeed was a pun on PoliteSpeed.


This is the core module of the PyLightspeed package. It contains the main classes for interacting with the various Lightspeed APIs.
The base class, LightspeedApi, contains the most simple and common logic for interacting with the Lightspeed API. All other
classes inherit from this class and add additional functionality as needed.

It is implemented so that all of the different APIs can be accessed in a common way - via the `api` object with . access to the resouces/edpoints,
as well as simplified access to CRUD operations on the resources and subresources.

Accessing and Objects
~~~~~~~~~~~~~~~~~~~~~

The ``api`` object provides access to each API resource, each of which
provides CRUD operations, depending on capabilities of the resource:

.. code-block:: python

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

.. code-block:: python

    api.ProductOptions.page(1)                  # GET /products/1/options - note that get doesn't work with only 1
    api.ProductOptions.get(1, 2)               # GET /products/1/options/2
    
And as helper methods on the parent resource:

.. code-block:: python

    #maybe not implemented yet
    api.Products.get(1).variants()              # GET /products/1/variants
    api.Products.get(1).variants(1)             # GET /products/1/variants/1

These subresources implement CRUD methods in exactly the same way as
regular resources:

.. code:: python

    api.Products.get(1).options(1).delete()

API connections by Series
~~~~~~~~~~~~~~~~~~~~~~~~~

pylightspeed.api module
-----------------------

.. automodule:: pylightspeed.api
   :members:
   :show-inheritance:
   :member-order: bysource