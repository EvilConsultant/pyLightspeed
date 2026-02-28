# Adding New Resources

Lightspeed has many endpoints that pyLightspeed does not yet cover. Adding support for a new endpoint is straightforward: create a resource file, inherit the right mix of base classes, set a few class attributes, and register it. This page walks through the full process for each series.

---

## How resource lookup works

When you write `lsr.ItemVendors`, the `ApiResourceWrapper` calls `str_to_class` which looks up a class named `{namespace}{string}` — i.e. `RSeriesItemVendors`. The namespace per series is:

| Series | API class | Namespace prefix |
|--------|-----------|-----------------|
| R-Series | `LightspeedRSeriesApi` | `RSeries` |
| C-Series | `LightspeedCSeriesApi` | `CSeries` |
| X-Series | `LightspeedXSeriesApi` | `XSeries` |
| E-Series | `LightspeedESeriesApi` | `ESeries` |

So `lsr.PurchaseOrders` → `RSeriesPurchaseOrders`, `lsc.Blogs` → `CSeriesBlogs`, and so on. The class must be importable from `pylightspeed.resources` (via `__init__.py`) when the module is first loaded.

---

## The mixin system

Resource classes are built by combining a **base** with **capability mixins**. Pick the base for the series, then stack on whatever operations the API endpoint actually supports.

### Series base classes

| Series | Import | Purpose |
|--------|--------|---------|
| `RSeriesApiResource` | `from ..rseries.rseriesbase import *` | R-Series pagination (offset/limit), field names |
| `XSeriesApiResource` | `from ..xseries.xseriesbase import *` | X-Series cursor pagination, field names |
| `ESeriesApiResource` | `from ..eseries.eseriesbase import *` | E-Series offset pagination, field names |
| (none / `ApiResource`) | `from ..base import *` | C-Series — use base directly with the mixins below |

### Capability mixins (from `base.py`)

| Mixin | Adds | Notes |
|-------|------|-------|
| `ListableApiResource` | `.page()`, `.listall()`, `.iterall()` | Almost always needed |
| `CreateableApiResource` | `.create()` | POST to collection |
| `UpdateableApiResource` | `.update()` | PUT using `self.id` (C / X / E) |
| `UpdateableRetailApiResource` | `.update()` | PUT using `self.{resource_id}` (R-Series) |
| `DeleteableApiResource` | `.delete()` | DELETE a single record |
| `CollectionDeleteableApiResource` | `.delete_all()` | DELETE entire collection |
| `CountableApiResource` | `.count()` | GET `/resource/count` |
| `ApiSubResource` | parent-aware path building | For nested endpoints |
| `ListableApiSubResource` | `.page()` on sub-resource | |
| `CreateableApiSubResource` | `.create(parentid, ...)` | |
| `UpdateableApiSubResource` | `.update()` | |
| `DeleteableApiSubResource` | `.delete()` | |
| `CollectionDeleteableApiSubResource` | `.delete_all(parentid)` | |
| `CountableApiSubResource` | `.count(parentid)` | |

---

## Step-by-step: adding a new top-level resource

### 1. Create the file

Place it in the right series folder:

```
src/pylightspeed/resources/
    rseries/   ← R-Series
    cseries/   ← C-Series
    xseries/   ← X-Series
    eseries/   ← E-Series
```

### 2. Write the class

**R-Series example** — `rseries/purchaseorders.py`

Check the [R-Series API reference](https://developers.lightspeedhq.com/retail/endpoints/purchaseorder/) for the endpoint name, ID field, and supported operations.

```python
from ..base import *
from .rseriesbase import *


class RSeriesPurchaseOrders(
    RSeriesApiResource,
    CreateableApiResource,
    UpdateableRetailApiResource,
    DeleteableApiResource,
):
    resource_name = "PurchaseOrder"  # exact URL segment from the API docs
    resource_id = "purchaseOrderID"  # field name that holds the record's ID
```

R-Series field names come from the API response — look for the `ID` field (e.g. `employeeID`, `vendorID`) and use that as `resource_id`.

**C-Series example** — `cseries/blogs.py`

```python
from ..base import *


class CSeriesBlogs(
    ListableApiResource,
    CreateableApiResource,
    UpdateableApiResource,
    DeleteableApiResource,
    CountableApiResource,
):
    resource_name = "blogs"  # lowercase URL slug
    # resource_id defaults to "id" — correct for C-Series
```

C-Series does not need a series base class — use the mixins from `base.py` directly.

**X-Series example** — `xseries/registers.py`

```python
from ..base import *
from .xseriesbase import *


class XSeriesRegisters(
    XSeriesApiResource,
    ListableApiResource,
):
    resource_name = "registers"
    # resource_id defaults to "id" — correct for X-Series
```

**E-Series example** — `eseries/customers.py`

```python
from ..base import *
from .eseriesbase import *


class ESeriesCustomers(
    ESeriesApiResource,
    ListableApiResource,
    CreateableApiResource,
    UpdateableApiResource,
    DeleteableApiResource,
):
    resource_name = "customers"
```

### 3. Register in `__init__.py`

Open `src/pylightspeed/resources/__init__.py` and add an import in the appropriate section:

```python
# R Series API objects
from .rseries.purchaseorders import *   # ← add this

# C Series API objects
from .cseries.blogs import *            # ← add this

# X Series API objects
from .xseries.registers import *        # ← add this

# E Series API objects
from .eseries.customers import *        # ← add this
```

### 4. Use it

```python
pos = lsr.PurchaseOrders.listall()
blogs = lsc.Blogs.page()
registers = lsx.Registers.listall()
customers = lse.Customers.get(12345678)
```

---

## Adding a sub-resource (nested endpoint)

Sub-resources live under a parent, e.g. `GET /products/{id}/images`. Use the `ApiSubResource` family of mixins and set `parent_resource` and `parent_key`.

**C-Series example** — a new sub-resource on an existing file, or its own file:

```python
class CSeriesBlogArticles(
    ListableApiSubResource,
    CreateableApiSubResource,
    UpdateableApiSubResource,
    DeleteableApiSubResource,
    CountableApiSubResource,
):
    resource_name = "articles"          # URL segment after the parent id
    parent_resource = "blogs"           # URL segment for the parent
    parent_key = "blog_id"              # field on the child object that holds the parent id
    count_resource = "blogs/articles"   # used by CountableApiSubResource when no parentid provided
```

Access it as an independent resource:

```python
articles = lsc.BlogArticles.page(parentid=42)   # GET /blogs/42/articles
article  = lsc.BlogArticles.get(42, 1)          # GET /blogs/42/articles/1
```

Or attach a helper method to the parent resource so it can be reached via dot notation:

```python
class CSeriesBlogs(...):
    resource_name = "blogs"

    def articles(self, id=None):
        """Return articles for this blog."""
        if id:
            return CSeriesBlogArticles.get(self.id, id, connection=self._connection)
        return CSeriesBlogArticles.page(parentid=self.id, connection=self._connection)
```

```python
blog = lsc.Blogs.get(42)
blog.articles()     # GET /blogs/42/articles
blog.articles(1)    # GET /blogs/42/articles/1
```

---

## Overriding methods

### Non-standard URL paths

If a resource uses a path that doesn't follow the `resource_name/id` convention, override the relevant path method:

```python
class XSeriesProducts(XSeriesApiResource, ...):
    resource_name = "products"

    def _update_path(self):
        # X-Series v2.1 PUT goes to a versioned path
        return "api/2.1/products/{}".format(self.id)
```

Available path methods to override:

| Method | Default | Override when |
|--------|---------|---------------|
| `_get_path(cls, id)` | `resource_name/id` | GET path differs |
| `_get_all_path(cls)` | `resource_name` | list path differs |
| `_create_path(cls)` | `resource_name` | POST path differs |
| `_update_path(self)` | `resource_name/self.id` | PUT path differs |
| `_delete_path(self)` | `resource_name/self.id` | DELETE path differs |
| `_count_path(cls)` | `resource_name/count` | count path differs |
| `full_path(self, url)` *(on Connection)* | prepends host + api_path | entire URL differs |

### Flattening nested response data

R-Series in particular returns deeply nested JSON. Override `nested_json_to_attr` to promote nested fields to top-level attributes so they are accessible via dot notation and included in `as_dict()`:

```python
class RSeriesPurchaseOrders(RSeriesApiResource, ...):
    resource_name = "PurchaseOrder"
    resource_id = "purchaseOrderID"

    def nested_json_to_attr(self):
        """Flatten commonly used nested fields."""
        try:
            self.vendor_name = self["Vendor"]["name"]
        except (KeyError, TypeError):
            self.vendor_name = None

        try:
            self.total = self["PurchaseOrderCustomFieldValues"]["total"]
        except (KeyError, TypeError):
            self.total = None
```

### Custom response unwrapping

R-Series wraps each response in a top-level key matching the resource name (e.g. `{"PurchaseOrder": {...}}`). The `RSeriesConnection._handle_result` method unwraps this automatically using `connection.resource`. You normally don't need to change this, but if an endpoint returns data under a different key, override `_handle_result` on the connection or call `page()` with custom params.

### Sync / incremental fetch

All resources that inherit `ListableApiResource` get a `sync_records(since=datetime)` class method that filters by `updated_at_min`. For R-Series resources, override it to use R-Series filter syntax:

```python
class RSeriesPurchaseOrders(RSeriesApiResource, ...):
    resource_name = "PurchaseOrder"
    resource_id = "purchaseOrderID"

    @classmethod
    def sync_records(cls, connection=None, since=None, **params):
        if since is not None:
            params["timeStamp"] = f">,{since.strftime('%Y-%m-%dT%H:%M:%S+0000')}"
        return cls.listall(connection=connection, **params)
```

---

## Quick reference: class name conventions

| Series | Pattern | Example endpoint | Class name |
|--------|---------|-----------------|-----------|
| R-Series | `RSeries{PascalCase}` | `PurchaseOrder` | `RSeriesPurchaseOrders` |
| C-Series | `CSeries{PascalCase}` | `blogs` | `CSeriesBlogs` |
| X-Series | `XSeries{PascalCase}` | `registers` | `XSeriesRegisters` |
| E-Series | `ESeries{PascalCase}` | `customers` | `ESeriesCustomers` |

The string after the namespace prefix is what you use when accessing the API object. `lsr.PurchaseOrders` → looks up `RSeriesPurchaseOrders`.

---

## Complete example: R-Series Gift Cards

Suppose you want to add `GiftCard` (see [R-Series GiftCard docs](https://developers.lightspeedhq.com/retail/endpoints/giftcard/)).

**`src/pylightspeed/resources/rseries/giftcards.py`**:

```python
# R-Series: GiftCards endpoint
# https://developers.lightspeedhq.com/retail/endpoints/giftcard/
from ..base import *
from .rseriesbase import *


class RSeriesGiftCards(
    RSeriesApiResource,
    CreateableApiResource,
    UpdateableRetailApiResource,
    DeleteableApiResource,
):
    resource_name = "GiftCard"
    resource_id = "giftCardID"

    def nested_json_to_attr(self):
        """Flatten balance from the nested structure."""
        try:
            self.balance = self["balance"]
        except (KeyError, TypeError):
            self.balance = None
```

**`src/pylightspeed/resources/__init__.py`** — add one line in the R-Series section:

```python
from .rseries.giftcards import *
```

**Usage:**

```python
cards = lsr.GiftCards.listall()
card  = lsr.GiftCards.get(1234)
new   = lsr.GiftCards.create(giftCardCode="ABCD1234", balance=50.0)
card.update(balance=25.0)
```
