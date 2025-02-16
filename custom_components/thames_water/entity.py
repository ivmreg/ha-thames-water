"""Entity for the Thames Water integration."""

from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class ThamesWaterEntity(Entity):
    """Base class for TW Entity."""

    @property
    def device_info(self):
        """Return device information for this entity."""
        return {
            "identifiers": {(DOMAIN, "thames_water")},
            "manufacturer": "Thames Water",
            "model": "Thames Water",
            "name": "Thames Water Meter",
        }
