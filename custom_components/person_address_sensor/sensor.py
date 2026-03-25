from __future__ import annotations

import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

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
)
from .geocoder import async_reverse_lookup

_LOGGER = logging.getLogger(__name__)


def _entry_setting(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Read a setting from options first, then fall back to data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    cache = hass.data[DOMAIN][entry.entry_id]["cache"]
    sensor = PersonAddressSensor(hass, entry, cache)
    hass.data[DOMAIN][entry.entry_id]["sensor"] = sensor
    async_add_entities([sensor], True)


class PersonAddressSensor(SensorEntity):
    """Combined address sensor for a selected person entity."""

    _attr_should_poll = False
    _attr_icon = "mdi:map-marker"
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cache) -> None:
        self.hass = hass
        self.entry = entry
        self.cache = cache

        self.person_entity_id: str = entry.data[CONF_PERSON_ENTITY_ID]
        self.fields: list[str] = list(
            _entry_setting(entry, CONF_FIELDS, DEFAULT_FIELDS)
        )
        self.interval: int = int(
            _entry_setting(entry, CONF_INTERVAL, DEFAULT_INTERVAL)
        )
        self.distance_threshold: int = int(
            _entry_setting(entry, CONF_DISTANCE_THRESHOLD, DEFAULT_DISTANCE_THRESHOLD)
        )
        self.prefer_zone: bool = bool(
            _entry_setting(entry, CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE)
        )

        self._person_name = self._resolve_person_name()
        self._attr_unique_id = f"{entry.entry_id}_combined_address"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

        self._last_lat: float | None = None
        self._last_lon: float | None = None
        self._last_update_ts: float | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for grouping under the integration."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=f"{self._person_name} Address Sensor",
            manufacturer="Onellan",
            model="Person Address Sensor",
        )

    async def async_added_to_hass(self) -> None:
        """Handle entity added to HA."""
        current_state = self.hass.states.get(self.person_entity_id)
        if current_state is not None:
            await self._async_process_state(current_state, force=True)

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

    async def async_force_refresh(self) -> None:
        """Force an immediate refresh from current coordinates."""
        state = self.hass.states.get(self.person_entity_id)
        if state is None:
            _LOGGER.warning(
                "Force refresh skipped for %s: person state not found",
                self.person_entity_id,
            )
            return

        _LOGGER.debug("Force refresh requested for %s", self.person_entity_id)
        await self._async_process_state(state, force=True)

    async def _async_process_state(self, state, force: bool = False) -> None:
        """Process current person state and update sensor."""
        lat = state.attributes.get(ATTR_LATITUDE)
        lon = state.attributes.get(ATTR_LONGITUDE)

        if lat is None or lon is None:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "person_entity_id": self.person_entity_id,
                "status": "no_coordinates",
            }
            self.async_write_ha_state()
            _LOGGER.warning(
                "No coordinates available for %s", self.person_entity_id
            )
            return

        now_ts = self.hass.loop.time()

        if not force and self._last_lat is not None and self._last_lon is not None:
            distance = _distance_meters(self._last_lat, self._last_lon, lat, lon)
            if distance < self.distance_threshold:
                _LOGGER.debug(
                    "Skipping update for %s: moved %.2f m, threshold is %s m",
                    self.person_entity_id,
                    distance,
                    self.distance_threshold,
                )
                return

        if (
            not force
            and self._last_update_ts is not None
            and (now_ts - self._last_update_ts) < self.interval
        ):
            _LOGGER.debug(
                "Skipping update for %s: interval not reached",
                self.person_entity_id,
            )
            return

        zone_name = None
        if self.prefer_zone:
            zone_name = _find_zone_name(self.hass, lat, lon)

        if zone_name:
            address_data: dict[str, Any] = {
                "zone": zone_name,
                "full_address": zone_name,
            }
            _LOGGER.debug(
                "Using zone '%s' for %s", zone_name, self.person_entity_id
            )
        else:
            cache_key = f"{round(lat, 6)},{round(lon, 6)}"
            address_data = {} if force else (await self.cache.async_get(cache_key) or {})

            if address_data:
                _LOGGER.debug("Using cached address for %s", self.person_entity_id)

            if not address_data:
                _LOGGER.debug(
                    "Reverse geocoding %s at lat=%s lon=%s",
                    self.person_entity_id,
                    lat,
                    lon,
                )
                looked_up = await async_reverse_lookup(self.hass, lat, lon)
                if looked_up is None:
                    _LOGGER.warning(
                        "Reverse geocoding returned no result for %s",
                        self.person_entity_id,
                    )
                    return
                address_data = looked_up
                await self.cache.async_set(cache_key, address_data)

        combined = self._format_selected_fields(address_data)

        self._person_name = self._resolve_person_name()
        self._attr_native_value = combined or None
        self._attr_extra_state_attributes = {
            "person_entity_id": self.person_entity_id,
            "selected_fields": self.fields,
            "latitude": lat,
            "longitude": lon,
            "force_update_supported": True,
            **address_data,
        }

        self._last_lat = lat
        self._last_lon = lon
        self._last_update_ts = now_ts

        self.async_write_ha_state()
        _LOGGER.debug(
            "Updated %s address sensor to '%s'",
            self.person_entity_id,
            self._attr_native_value,
        )

    def _resolve_person_name(self) -> str:
        """Resolve person display name."""
        state = self.hass.states.get(self.person_entity_id)
        if state and state.name:
            return state.name
        return self.person_entity_id

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
    radius = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return radius * c


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