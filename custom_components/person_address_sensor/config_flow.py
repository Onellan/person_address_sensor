"""Config flow for Person Address Sensor."""
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

DATA_SCHEMA = vol.Schema({
    vol.Required("name"): str,
    vol.Optional("entity_id"): str,
})

class PersonAddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)