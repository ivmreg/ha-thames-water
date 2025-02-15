"""Number platform for the Thames Water integration."""

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities for Thames Water."""
    # Create minimal device_info.
    device_info = DeviceInfo(
        identifiers={(DOMAIN, "thames_water")},
        manufacturer="Thames Water",
        model="Thames Water",
        name="Thames Water Meter",
    )

    # Get values first from options, falling back to entry.data.
    liter_cost = entry.options.get("liter_cost", entry.data.get("liter_cost"))

    entities = [
        ThamesWaterLiterCost(device_info, entry, initial_value=liter_cost),
    ]
    async_add_entities(entities)


class ThamesWaterLiterCost(NumberEntity):
    """Number entity representing the water liter cost in GBP/L as a normal input box."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Liter Cost"
    _attr_native_unit_of_measurement = "GBP/L"
    _attr_native_max_value = 1.0
    _attr_native_min_value = 0.00005
    _attr_native_step = 0.00005
    _attr_icon = "mdi:currency-gbp"
    _attr_mode = "box"

    def __init__(
        self,
        device_info: DeviceInfo,
        config_entry: ConfigEntry,
        initial_value: float = 0.0,
    ) -> None:
        """Initialize the Thames Water Liter Cost number entity."""
        self._device_info = device_info
        self._config_entry = config_entry
        # Save the value as a float.
        self._value = float(initial_value)
        self._attr_unique_id = f"{config_entry.entry_id}_liter_cost"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return self._device_info

    @property
    def native_value(self) -> float:
        """Return the liter cost value."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Handle user changes by updating both local value and config options."""
        self._value = value
        new_options = dict(self._config_entry.options)
        new_options["liter_cost"] = value
        self.hass.config_entries.async_update_entry(
            self._config_entry, options=new_options
        )
        self.async_write_ha_state()
