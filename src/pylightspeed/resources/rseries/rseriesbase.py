from ..base import *


class RSeriesApiResource(ApiResource):
    # The various APIs and endpoints of Lightspeed have different names for important fields. This class gives us the
    # flexibility to allow us to override the default values for the resource name, id, and created_at/updated_at fields.
    # X Series uses id, created_at, and updated_at for all endpoints, so we can set that here.
    created_at = "createTime"
    updated_at = "timeStamp"


class DeleteableRSeriesApiResource(DeleteableApiResource):
    def _delete_path(self):
        return "%s/%s" % (self.resource_name, getattr(self, self.resource_id))
