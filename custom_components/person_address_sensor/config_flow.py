from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_PERSON_ENTITY_ID,
    CONF_FIELDS,
    CONF_INTERVAL,
    CONF_DISTANCE_THRESHOLD,
    CONF_PREFER_ZONE,
    DEFAULT_FIELDS,
    DEFAULT_INTERVAL,
    DEFAULT_DISTANCE_THRESHOLD,
    DEFAULT_PREFER_ZONE,
)


def _person_selector(hass):
    persons = [
        entity.entity_id
        for entity in hass.states.async_all("person")
    ]

    return selector(
        {
            "select": {
                "options": persons,
                "mode": "dropdown",
            }
        }
    )


class PersonAddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_PERSON_ENTITY_ID],
                data={
                    CONF_PERSON_ENTITY_ID: user_input[CONF_PERSON_ENTITY_ID],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_PERSON_ENTITY_ID): _person_selector(self.hass),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    # ✅ NEW: Proper reconfigure flow
    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_PERSON_ENTITY_ID: user_input[CONF_PERSON_ENTITY_ID],
                },
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PERSON_ENTITY_ID,
                    default=entry.data.get(CONF_PERSON_ENTITY_ID),
                ): _person_selector(self.hass),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PersonAddressOptionsFlow(config_entry)


class PersonAddressOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_FIELDS,
                    default=options.get(CONF_FIELDS, DEFAULT_FIELDS),
                ): cv.multi_select(
                    {
                        "street": "Street",
                        "suburb": "Suburb",
                        "city": "City",
                        "province": "Province",
                        "country": "Country",
                    }
                ),
                vol.Optional(
                    CONF_INTERVAL,
                    default=options.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                ): selector(
                    {
                        "number": {
                            "min": 10,
                            "max": 3600,
                            "unit_of_measurement": "seconds",
                        }
                    }
                ),
                vol.Optional(
                    CONF_DISTANCE_THRESHOLD,
                    default=options.get(
                        CONF_DISTANCE_THRESHOLD, DEFAULT_DISTANCE_THRESHOLD
                    ),
                ): selector(
                    {
                        "number": {
                            "min": 0,
                            "max": 500,
                            "unit_of_measurement": "meters",
                        }
                    }
                ),
                vol.Optional(
                    CONF_PREFER_ZONE,
                    default=options.get(
                        CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE
                    ),
                ): selector(
                    {"boolean": {}}
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)