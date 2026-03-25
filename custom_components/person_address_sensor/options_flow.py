from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN, FIELD_OPTIONS

class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(
                "fields",
                default=self.config_entry.options.get("fields", ["full_address"])
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=FIELD_OPTIONS,
                    multiple=True,
                    mode="dropdown",
                )
            ),
            vol.Optional(
                "interval",
                default=self.config_entry.options.get("interval", 300)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=60,
                    max=3600,
                    step=60,
                )
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)