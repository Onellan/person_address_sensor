from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_state_change_event

from .cache import AddressCache
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
    CACHE_FILE,
)
from .geocoder import async_reverse_lookup


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up sensor entities from a config entry."""
    cache = AddressCache(hass, Path(hass.config.path(CACHE_FILE)))
    await cache.async_load()

    async_add_entities(
        [
            PersonAddressSensor(hass, entry, cache),
        ],
        True,
    )


class PersonAddressSensor(SensorEntity):
    """Combined address sensor for a selected person entity."""

    _attr_should_poll = False
    _attr_icon = "mdi:map-marker"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cache: AddressCache) -> None:
        self.hass = hass
        self.entry = entry
        self.cache = cache

        self.person_entity_id: str = entry.data[CONF_PERSON_ENTITY_ID]
        self.fields: list[str] = entry.options.get(CONF_FIELDS, DEFAULT_FIELDS)
        self.interval: int = int(entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        self.distance_threshold: int = int(
            entry.options.get(CONF_DISTANCE_THRESHOLD, DEFAULT_DISTANCE_THRESHOLD)
        )
        self.prefer_zone: bool = bool(entry.options.get(CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE))

        state = hass.states.get(self.person_entity_id)
        person_name = state.name if state else self.person_entity_id

        self._attr_name = f"{person_name} Address"
        self._attr_unique_id = f"{entry.entry_id}_combined_address"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        self._last_lat: float | None = None
        self._last_lon: float | None = None
        self._last_update_ts: float | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to HA."""
        current_state = self.hass.states.get(self.person_entity_id)
        if current_state is not None:
            await self._async_process_state(current_state)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.person_entity_id],
                self._async_handle_state_event,
            )
        )

    @callback
    def _async_handle_state_event(self, event) -> None:
        """Handle person state-change event."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        self.hass.async_create_task(self._async_process_state(new_state))

    async def _async_process_state(self, state) -> None:
        """Process current person state and update sensor."""
        lat = state.attributes.get("latitude")
        lon = state.attributes.get("longitude")

        if lat is None or lon is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "person_entity_id": self.person_entity_id,
                "status": "no_coordinates",
            }
            self.async_write_ha_state()
            return

        now_ts = self.hass.loop.time()

        if self._last_lat is not None and self._last_lon is not None:
            distance = _distance_meters(self._last_lat, self._last_lon, lat, lon)
            if distance < self.distance_threshold:
                return

        if self._last_update_ts is not None and (now_ts - self._last_update_ts) < self.interval:
            return

        zone_name = None
        if self.prefer_zone:
            zone_name = _find_zone_name(self.hass, lat, lon)

        if zone_name:
            address_data: dict[str, Any] = {
                "zone": zone_name,
                "full_address": zone_name,
            }
        else:
            cache_key = f"{round(lat, 6)},{round(lon, 6)}"
            address_data = await self.cache.async_get(cache_key) or {}

            if not address_data:
                looked_up = await async_reverse_lookup(self.hass, lat, lon)
                if looked_up is None:
                    return
                address_data = looked_up
                await self.cache.async_set(cache_key, address_data)

        combined = self._format_selected_fields(address_data)

        self._attr_native_value = combined or None
        self._attr_extra_state_attributes = {
            "person_entity_id": self.person_entity_id,
            "selected_fields": self.fields,
            "latitude": lat,
            "longitude": lon,
            **address_data,
        }

        self._last_lat = lat
        self._last_lon = lon
        self._last_update_ts = now_ts

        self.async_write_ha_state()

    def _format_selected_fields(self, address_data: dict[str, Any]) -> str:
        """Build one comma-separated string from selected fields."""
        if self.prefer_zone and address_data.get("zone") and "zone" in self.fields:
            return str(address_data["zone"])

        values: list[str] = []
        for field in self.fields:
            value = address_data.get(field)
            if value:
                values.append(str(value))

        return ", ".join(values)
        

def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return approximate Haversine distance in meters."""
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return r * c


def _find_zone_name(hass: HomeAssistant, lat: float, lon: float) -> str | None:
    """Return matching HA zone name if coordinates fall inside a zone."""
    for zone_state in hass.states.async_all("zone"):
        z_lat = zone_state.attributes.get("latitude")
        z_lon = zone_state.attributes.get("longitude")
        radius = zone_state.attributes.get("radius")

        if z_lat is None or z_lon is None or radius is None:
            continue

        if _distance_meters(lat, lon, z_lat, z_lon) <= float(radius):
            return zone_state.name

    return None