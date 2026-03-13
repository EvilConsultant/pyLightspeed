import warnings


class LightspeedStore:
    """.. deprecated::
        ``LightspeedStore`` has been removed in pyLightspeed 2.0.

        Replace with :class:`~pylightspeed.connection.VaultTokenStore` (primary) backed
        by :class:`~pylightspeed.connection.StoresTableTokenStore` (fallback), composed
        via :class:`~pylightspeed.connection.CompositeTokenStore`. See the
        ``migrate-to-v2`` skill for step-by-step instructions.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "LightspeedStore has been removed in pyLightspeed 2.0. "
            "Replace with VaultTokenStore (primary) + StoresTableTokenStore (fallback) "
            "via CompositeTokenStore. See the migrate-to-v2 skill for details.",
            DeprecationWarning,
            stacklevel=2,
        )
        raise RuntimeError(
            "LightspeedStore has been removed in pyLightspeed 2.0. "
            "Replace with VaultTokenStore (primary) + StoresTableTokenStore (fallback) "
            "via CompositeTokenStore. See the migrate-to-v2 skill for details."
        )

    def save_codes(self):
        raise RuntimeError("LightspeedStore has been removed in pyLightspeed 2.0.")

