# https://docs.vendhq.com/reference/

from ..base import *
from .xseriesbase import *


class XSeriesSuppliers(XSeriesApiResource, ListableApiResource, CreateableApiResource,
               UpdateableApiResource, DeleteableApiResource,
               CollectionDeleteableApiResource, CountableApiResource):
    api_path = "/api/{}"
    resource_name = 'suppliers'

    
    
#     {"vendorID":"1","name":"Southern Wine & Spirits","archived":"false","accountNumber":"","priceLevel":"","updatePrice":"false","updateCost":"false","updateDescription":"false","shareSellThrough":"false","timeStamp":"2019-03-23T20:19:24+00:00",
# "Contact":{"contactID":"5","custom":"","noEmail":"true","noPhone":"true","noMail":"true",
#            "Addresses":{"ContactAddress":{"address1":"","address2":"","city":"","state":"","zip":"","country":"","countryCode":"","stateCode":""}},"Phones":"","Emails":"","Websites":"","timeStamp":"2019-03-23T20:19:24+00:00"}}}'