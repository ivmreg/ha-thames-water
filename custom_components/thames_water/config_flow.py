"""Config flow for Thames Water integration."""

import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class ThamesWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Thames Water."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate liter_cost
            liter_cost_str = user_input.get("liter_cost")
            try:
                liter_cost_val = float(liter_cost_str)
                if liter_cost_val < 0.00005 or liter_cost_val > 1.0:
                    errors["liter_cost"] = "Value must be between 0.00005 and 1.0"
            except (TypeError, ValueError):
                errors["liter_cost"] = "Not a valid number"

            if not errors:
                # Replace string values with validated floats
                user_input["liter_cost"] = liter_cost_val
                return self.async_create_entry(title="Thames Water", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    "username", description={"suggested_value": "email@email.com"}
                ): str,
                vol.Required("password"): str,
                vol.Required("account_number"): str,
                vol.Required("meter_id"): str,
                vol.Required("liter_cost", default="0.0030682"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
