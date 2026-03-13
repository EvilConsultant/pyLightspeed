# Use this as a template for new resources

# Importing base provides access to all the base classes.
# Make sure you also edit the __init__.py file in the resources directory to include your new resource
from .base import *
from .rseries.rseriesbase import RSeriesApiResource

# The class name pluralized and titlecased — this is used to build the API endpoint for api.Templates.
# resource_name = 'Template' is the exact Lightspeed endpoint name (e.g. 'Template.json' for R-Series).
# R-Series endpoint names are CamelCase; C/X/E-Series are lowercase.
# resource_id = 'templateID' is the primary key. R-Series resources have unique keys; C/X/E default to 'id'.

# R-Series resource:
class Templates(RSeriesApiResource, CreateableApiResource, UpdateableRetailApiResource, DeleteableApiResource):
    resource_name = 'Template'
    resource_id = 'templateID'

# C/X/E-Series resource:
# class Templates(ListableApiResource, CreateableApiResource, UpdateableApiResource, DeleteableApiResource):
#     resource_name = 'templates'
#     resource_id = 'id'