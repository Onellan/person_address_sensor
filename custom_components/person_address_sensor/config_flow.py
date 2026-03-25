from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

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


def _build_schema(
    *,
    person_default: str | None = None,
    fields_default: list[str] | None = None,
    interval_default: int = DEFAULT_INTERVAL,
    distance_default: int = DEFAULT_DISTANCE_THRESHOLD,
    prefer_zone_default: bool = DEFAULT_PREFER_ZONE,
    include_person: bool = True,
) -> vol.Schema:
    schema: dict[Any, Any] = {}

    if include_person:
        schema[
            vol.Required(
                CONF_PERSON_ENTITY_ID,
                default=person_default,
            )
        ] = EntitySelector(EntitySelectorConfig(domain="person"))

    schema[
        vol.Required(
            CONF_FIELDS,
            default=fields_default or DEFAULT_FIELDS,
        )
    ] = SelectSelector(
        SelectSelectorConfig(
            options=FIELD_OPTIONS,
            multiple=True,
            mode="dropdown",
        )
    )

    schema[
        vol.Required(
            CONF_INTERVAL,
            default=interval_default,
        )
    ] = NumberSelector(
        NumberSelectorConfig(
            min=60,
            max=86400,
            step=60,
            mode="box",
        )
    )

    schema[
        vol.Required(
            CONF_DISTANCE_THRESHOLD,
            default=distance_default,
        )
    ] = NumberSelector(
        NumberSelectorConfig(
            min=0,
            max=5000,
            step=5,
            mode="box",
        )
    )

    schema[
        vol.Required(
            CONF_PREFER_ZONE,
            default=prefer_zone_default,
        )
    ] = BooleanSelector()

    return vol.Schema(schema)


class PersonAddressSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Person Address Sensor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            person_entity_id = user_input[CONF_PERSON_ENTITY_ID]
            await self.async_set_unique_id(person_entity_id)
            self._abort_if_unique_id_configured()

            state = self.hass.states.get(person_entity_id)
            title = state.name if state else person_entity_id

            return self.async_create_entry(
                title=title,
                data={
                    CONF_PERSON_ENTITY_ID: person_entity_id,
                },
                options={
                    CONF_FIELDS: user_input[CONF_FIELDS],
                    CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                    CONF_DISTANCE_THRESHOLD: int(user_input[CONF_DISTANCE_THRESHOLD]),
                    CONF_PREFER_ZONE: bool(user_input[CONF_PREFER_ZONE]),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return PersonAddressSensorOptionsFlow()


class PersonAddressSensorOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Person Address Sensor."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_FIELDS: user_input[CONF_FIELDS],
                    CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                    CONF_DISTANCE_THRESHOLD: int(user_input[CONF_DISTANCE_THRESHOLD]),
                    CONF_PREFER_ZONE: bool(user_input[CONF_PREFER_ZONE]),
                },
            )

        current_options = self.config_entry.options
        current_data = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                person_default=current_data.get(CONF_PERSON_ENTITY_ID),
                fields_default=current_options.get(CONF_FIELDS, DEFAULT_FIELDS),
                interval_default=current_options.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                distance_default=current_options.get(
                    CONF_DISTANCE_THRESHOLD, DEFAULT_DISTANCE_THRESHOLD
                ),
                prefer_zone_default=current_options.get(
                    CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE
                ),
                include_person=False,
            ),
        )