# Use this as a template for new resources

# Importing base provides access to all the base classes.
# Make sure you also edit the __init__.py file in the resources directory to include your new resource
from .base import *

# the class name pluralized and titlecased. This is used to build the API endpoint for api.Templates. Don't camelcase or it won't work.
# resource_name = 'Template' is the exact name of the Lightspeed endpoint. resource_name becomes the resource_name.json for the endpoint. 
# Note that Lightspeed Retail is caps and eCom is lower case for the endpoint name.
# resource_id = 'templateID' is the primary key for the resource.
# While resource_id is not used specifically in the api, it is there so other things (like database models) can know what the primary key is.
# All ecommerce resources have a resource_id of 'id' because that is the primary key for the ecommerce database so that is then base class ID, 
# but Retail resources have different primary keys and need to be overridden.

class Templates(ListableRetailApiResource, CreateableApiResource,
               UpdateableRetailApiResource, DeleteableApiResource):
    resource_name = 'Template'
    resource_id = 'templateID'