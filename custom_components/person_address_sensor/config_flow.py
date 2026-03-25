from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import selector

from .const import (
    CONF_DISTANCE_THRESHOLD,
    CONF_FIELDS,
    CONF_INTERVAL,
    CONF_PERSON_ENTITY_ID,
    CONF_PREFER_ZONE,
    DEFAULT_DISTANCE_THRESHOLD,
    DEFAULT_FIELDS,
    DEFAULT_INTERVAL,
    DEFAULT_PREFER_ZONE,
    DOMAIN,
    FIELD_OPTIONS,
)


def _person_selector(hass) -> dict[str, Any]:
    """Build a selector for available person entities."""
    persons = sorted(entity.entity_id for entity in hass.states.async_all("person"))

    return selector(
        {
            "select": {
                "options": persons,
                "mode": "dropdown",
            }
        }
    )


def _field_labels() -> dict[str, str]:
    """Return labels for supported address fields."""
    return {
        "full_address": "Full address",
        "house_number": "House number",
        "road": "Road / street",
        "suburb": "Suburb",
        "neighbourhood": "Neighbourhood",
        "city": "City / town",
        "county": "County",
        "state": "State / province",
        "postcode": "Postcode",
        "country": "Country",
        "country_code": "Country code",
        "zone": "Home Assistant zone",
    }


def _sanitize_fields(fields: list[str] | None) -> list[str]:
    """Keep only valid fields, preserving order."""
    if not fields:
        return list(DEFAULT_FIELDS)

    valid = [field for field in fields if field in FIELD_OPTIONS]
    return valid or list(DEFAULT_FIELDS)


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for configurable sensor settings."""
    return vol.Schema(
        {
            vol.Required(
                CONF_FIELDS,
                default=_sanitize_fields(defaults.get(CONF_FIELDS)),
            ): cv.multi_select(_field_labels()),
            vol.Required(
                CONF_INTERVAL,
                default=int(defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
            ): selector(
                {
                    "number": {
                        "min": 10,
                        "max": 3600,
                        "mode": "box",
                        "unit_of_measurement": "seconds",
                    }
                }
            ),
            vol.Required(
                CONF_DISTANCE_THRESHOLD,
                default=int(
                    defaults.get(CONF_DISTANCE_THRESHOLD, DEFAULT_DISTANCE_THRESHOLD)
                ),
            ): selector(
                {
                    "number": {
                        "min": 0,
                        "max": 5000,
                        "mode": "box",
                        "unit_of_measurement": "meters",
                    }
                }
            ),
            vol.Required(
                CONF_PREFER_ZONE,
                default=bool(defaults.get(CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE)),
            ): selector({"boolean": {}}),
        }
    )


def _combined_user_schema(hass, defaults: dict[str, Any]) -> vol.Schema:
    """Schema for first-time setup."""
    return vol.Schema(
        {
            vol.Required(
                CONF_PERSON_ENTITY_ID,
                default=defaults.get(CONF_PERSON_ENTITY_ID),
            ): _person_selector(hass),
            **_settings_schema(defaults).schema,
        }
    )


def _entry_setting(entry, key: str, default: Any) -> Any:
    """Read a setting from options first, then legacy data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


class PersonAddressConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Person Address Sensor."""

    VERSION = 3

    async def async_step_user(self, user_input=None):
        """Handle the initial setup flow."""
        if user_input is not None:
            person_entity_id = user_input[CONF_PERSON_ENTITY_ID]

            await self.async_set_unique_id(person_entity_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=person_entity_id,
                data={
                    CONF_PERSON_ENTITY_ID: person_entity_id,
                    CONF_FIELDS: _sanitize_fields(user_input[CONF_FIELDS]),
                    CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                    CONF_DISTANCE_THRESHOLD: int(
                        user_input[CONF_DISTANCE_THRESHOLD]
                    ),
                    CONF_PREFER_ZONE: bool(user_input[CONF_PREFER_ZONE]),
                },
            )

        defaults = {
            CONF_FIELDS: DEFAULT_FIELDS,
            CONF_INTERVAL: DEFAULT_INTERVAL,
            CONF_DISTANCE_THRESHOLD: DEFAULT_DISTANCE_THRESHOLD,
            CONF_PREFER_ZONE: DEFAULT_PREFER_ZONE,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=_combined_user_schema(self.hass, defaults),
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle changing the tracked person for an existing entry."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            new_person = user_input[CONF_PERSON_ENTITY_ID]

            existing_entry = next(
                (
                    existing
                    for existing in self._async_current_entries()
                    if existing.entry_id != entry.entry_id
                    and (
                        existing.unique_id == new_person
                        or existing.data.get(CONF_PERSON_ENTITY_ID) == new_person
                    )
                ),
                None,
            )
            if existing_entry is not None:
                return self.async_abort(reason="already_configured")

            self.hass.config_entries.async_update_entry(
                entry,
                title=new_person,
                unique_id=new_person,
                data={
                    **entry.data,
                    CONF_PERSON_ENTITY_ID: new_person,
                },
            )

            return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PERSON_ENTITY_ID,
                        default=entry.data.get(CONF_PERSON_ENTITY_ID),
                    ): _person_selector(self.hass),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return PersonAddressOptionsFlow(config_entry)


class PersonAddressOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Person Address Sensor."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_FIELDS: _sanitize_fields(user_input[CONF_FIELDS]),
                    CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                    CONF_DISTANCE_THRESHOLD: int(
                        user_input[CONF_DISTANCE_THRESHOLD]
                    ),
                    CONF_PREFER_ZONE: bool(user_input[CONF_PREFER_ZONE]),
                },
            )

        defaults = {
            CONF_FIELDS: _entry_setting(
                self.config_entry, CONF_FIELDS, DEFAULT_FIELDS
            ),
            CONF_INTERVAL: _entry_setting(
                self.config_entry, CONF_INTERVAL, DEFAULT_INTERVAL
            ),
            CONF_DISTANCE_THRESHOLD: _entry_setting(
                self.config_entry,
                CONF_DISTANCE_THRESHOLD,
                DEFAULT_DISTANCE_THRESHOLD,
            ),
            CONF_PREFER_ZONE: _entry_setting(
                self.config_entry, CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(defaults),
        )