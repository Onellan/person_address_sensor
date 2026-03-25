"""Options flow for Person Address Sensor."""
import voluptuous as vol
from homeassistant import config_entries

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        options_schema = vol.Schema({
            vol.Optional(
                "fields",
                default=self.config_entry.options.get("fields", [])
            ): list,
        })

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=options_schema)