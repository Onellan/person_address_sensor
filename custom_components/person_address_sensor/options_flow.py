from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import selector


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        super().__init__(config_entry)


    async def async_step_init(self, user_input=None):

        if user_input is not None:

            return self.async_create_entry(
                title="",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    "interval",
                    default=self.config_entry.options.get(
                        "interval",
                        self.config_entry.data.get("interval", 300),
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=3600,
                        step=60,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )