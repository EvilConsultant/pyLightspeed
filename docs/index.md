# pyLightspeed

**pyLightspeed** is a Python wrapper for Lightspeed's various API series, providing consistent access to R-Series (Retail), C-Series (eCom), X-Series (Retail X), and E-Series (Ecwid) APIs. Based on the BigCommerce API wrapper pattern, it provides dot-notation access to resources and endpoints to make scripting and moving data around much easier.

Check out the [Usage](usage.md) section to get started, or the [Connections](connection.md) guide for authentication details.

!!! note
    This project is under active development.

## Quick Start

```python
from pylightspeed.api import LightspeedRSeriesApi, LightspeedCSeriesApi

lsr = LightspeedRSeriesApi(
    account_id="123456",
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_file="/path/to/codes.json",
)

lsc = LightspeedCSeriesApi(
    api_key="your_api_key",
    api_secret="your_api_secret",
)

# Fetch data from both
rseries_items = lsr.Items.listall()
cseries_products = lsc.Products.listall()
```

## Supported Series

| Series | API | Authentication |
|--------|-----|----------------|
| **R-Series** | Lightspeed Retail | OAuth 2.0 |
| **C-Series** | Lightspeed eCom | HTTP Basic Auth |
| **X-Series** | Lightspeed Retail X | OAuth 2.0 or Personal Access Token |
| **E-Series** | Ecwid | API secret (query param) |
