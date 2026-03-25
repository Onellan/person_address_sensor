"""Config flow for Person Address Sensor."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry
from homeassistant.core import callback
from .const import DOMAIN

class PersonAddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step with a dropdown of person entities."""
        persons = [
            entity.entity_id
            for entity in self.hass.states.async_all("person")
        ]
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["person_entity_id"],
                data=user_input
            )

        schema = vol.Schema({
            vol.Required("person_entity_id"): vol.In(persons)
        })
        return self.async_show_form(step_id="user", data_schema=schema)