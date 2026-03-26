from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up button entities for a config entry."""
    async_add_entities([PersonAddressForceUpdateButton(hass, entry)])


class PersonAddressForceUpdateButton(ButtonEntity):
    """Button to force a reverse-geocode refresh for this person sensor."""

    _attr_has_entity_name = True
    _attr_name = "Force update"
    _attr_icon = "mdi:refresh"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_force_update"

    @property
    def _sensor(self):
        """Return the current live sensor instance."""
        return self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {}).get("sensor")

    @property
    def available(self) -> bool:
        """Return whether the linked sensor is available."""
        return self._sensor is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for grouping under the same device."""
        sensor = self._sensor
        sensor_name = sensor.person_name if sensor is not None else self.entry.title
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"{sensor_name} Address Sensor",
            manufacturer="Onellan",
            model="Person Address Sensor",
        )

    async def async_press(self) -> None:
        """Force a refresh of the linked sensor."""
        sensor = self._sensor
        if sensor is None:
            _LOGGER.warning(
                "Force update pressed for %s but sensor instance was not available",
                self.entry.title,
            )
            return

        _LOGGER.warning("Force update button pressed for %s", sensor.person_name)
        await sensor.async_force_refresh()
