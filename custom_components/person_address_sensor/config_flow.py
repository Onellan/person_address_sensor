"""Config flow for Person Address Sensor."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

DEFAULT_FIELDS = ["address", "city", "country", "state", "zip"]


class PersonAddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial step: select person entity and fields."""
        # Get all person entities for dropdown
        persons = [
            entity.entity_id
            for entity in self.hass.states.async_all("person")
        ]

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["person_entity_id"],
                data={"person_entity_id": user_input["person_entity_id"]},
                options={"fields": user_input.get("fields", DEFAULT_FIELDS)},
            )

        schema = vol.Schema(
            {
                vol.Required("person_entity_id"): vol.In(persons),
                vol.Optional("fields", default=DEFAULT_FIELDS): vol.MultiSelect(
                    DEFAULT_FIELDS
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)