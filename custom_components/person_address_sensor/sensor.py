"""Sensor platform for Person Address Sensor."""
import json
from pathlib import Path
from homeassistant.helpers.event import async_track_state_change
from homeassistant.components.sensor import SensorEntity
from .cache import AddressCache

DOMAIN = "person_address_sensor"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor from a config entry."""
    cache_path = hass.config.path("person_address_cache.json")
    cache = AddressCache(cache_path, hass)
    await cache.load()

    entity_id = entry.data["person_entity_id"]
    selected_fields = entry.options.get("fields", ["address", "city", "country"])

    sensors = [PersonAddressSensor(entry, cache, entity_id, selected_fields)]
    async_add_entities(sensors, True)


class PersonAddressSensor(SensorEntity):
    """Sensor that combines selected address fields of a person."""

    def __init__(self, entry, cache, entity_id, fields):
        self._entry = entry
        self._cache = cache
        self._entity_id = entity_id
        self._fields = fields
        self._state = None

    @property
    def name(self):
        # Fixed TypeError: use property, not method
        return f"{self._entry.title} Address"

    @property
    def state(self):
        return self._state

    async def async_added_to_hass(self):
        """Track state changes for the person entity."""
        async_track_state_change(
            self.hass, [self._entity_id], self._async_state_changed
        )

    async def _async_state_changed(self, entity_id, old_state, new_state):
        """Update sensor state on person entity change."""
        if new_state is None:
            return

        addr = new_state.attributes.get("address", {})
        combined_parts = []
        for field in self._fields:
            value = addr.get(field, "")
            if value:
                combined_parts.append(f"{field}: {value}")

        self._state = ", ".join(combined_parts) if combined_parts else None

        await self.async_update_cache(addr)
        self.async_write_ha_state()

    async def async_update_cache(self, addr_data):
        """Save to cache async-safe."""
        self._cache.cache[self._entry.entry_id] = addr_data
        await self._cache.save()