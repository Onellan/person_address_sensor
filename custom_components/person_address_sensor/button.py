from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up button entities for a config entry."""
    sensor = hass.data[DOMAIN][entry.entry_id]["sensor"]
    async_add_entities([PersonAddressForceUpdateButton(entry, sensor)])


class PersonAddressForceUpdateButton(ButtonEntity):
    """Button to force a reverse-geocode refresh for this person sensor."""

    _attr_has_entity_name = True
    _attr_name = "Force update"
    _attr_icon = "mdi:refresh"

    def __init__(self, entry: ConfigEntry, sensor) -> None:
        self.entry = entry
        self.sensor = sensor
        self._attr_unique_id = f"{entry.entry_id}_force_update"

    @property
    def available(self) -> bool:
        """Return whether the linked sensor is available."""
        return self.sensor is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for grouping under the same device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"{self.entry.title} Address Sensor",
            manufacturer="Onellan",
            model="Person Address Sensor",
            configuration_url="homeassistant://config/integrations/integration/person_address_sensor",
        )

    async def async_press(self) -> None:
        """Force a refresh of the linked sensor."""
        if self.sensor is not None:
            await self.sensor.async_force_refresh()