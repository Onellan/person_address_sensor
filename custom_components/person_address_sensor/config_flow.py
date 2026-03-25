from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN
from .options_flow import OptionsFlowHandler


FIELD_OPTIONS = [
    "full_address",
    "street",
    "suburb",
    "city",
    "province",
    "zone",
]


class PersonAddressSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):

        if user_input is not None:

            return self.async_create_entry(
                title=user_input["person"],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required("person"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="person")
                ),

                vol.Required(
                    "fields",
                    default=["full_address"],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=FIELD_OPTIONS,
                        multiple=True,
                        mode="dropdown",
                    )
                ),

                vol.Required(
                    "interval",
                    default=300,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60,
                        max=3600,
                        step=60,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)
    