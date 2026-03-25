from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import FIELD_OPTIONS

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = {
            "fields": selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=FIELD_OPTIONS,
                    multiple=True,
                    mode="dropdown"
                )
            ),
            "interval": selector.NumberSelector(
                selector.NumberSelectorConfig(min=60, max=3600, step=60)
            )
        }
        return self.async_show_form(step_id="init", data_schema=schema)