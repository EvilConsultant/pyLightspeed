# API Reference Overview

pyLightspeed provides a consistent interface to all Lightspeed API series. This page gives a high-level overview of the module structure; see the individual reference pages for full class and method documentation.

## Module Structure

| Module | Contents |
|--------|----------|
| `pylightspeed.api` | Top-level API classes (`LightspeedRSeriesApi`, `LightspeedCSeriesApi`, `LightspeedXSeriesApi`, `LightspeedESeriesApi`) |
| `pylightspeed.connection` | Connection classes, `TokenStore`, `FileTokenStore` |
| `pylightspeed.exception` | Exception hierarchy |
| `pylightspeed.store` | `LightspeedStore` helper for multi-store workflows |
| `pylightspeed.resources` | Resource classes for each series (auto-loaded) |

## API Classes

```python
from pylightspeed.api import (
    LightspeedRSeriesApi,   # Lightspeed Retail (R-Series)
    LightspeedCSeriesApi,   # Lightspeed eCom (C-Series)
    LightspeedXSeriesApi,   # Lightspeed Retail X (X-Series)
    LightspeedESeriesApi,   # Ecwid (E-Series)
)
```

Each class exposes resources via dot notation:

```python
lsr.Items.listall()
lsc.Products.get(123)
lsx.Customers.page(email="user@example.com")
lse.Orders.iterall()
```

See the [Usage guide](usage.md) for full examples.

## Connecting and Authenticating

See the [Connections guide](connection.md) for detailed authentication instructions for each series.
