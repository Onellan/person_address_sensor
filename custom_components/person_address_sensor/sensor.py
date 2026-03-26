from __future__ import annotations

import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_DISTANCE_THRESHOLD,
    CONF_FIELDS,
    CONF_INTERVAL,
    CONF_PERSON_ENTITY_ID,
    CONF_PREFER_ZONE,
    CONF_UPDATE_RULES,
    DEFAULT_DISTANCE_THRESHOLD,
    DEFAULT_FIELDS,
    DEFAULT_INTERVAL,
    DEFAULT_PREFER_ZONE,
    DEFAULT_UPDATE_RULES,
    DOMAIN,
)
from .geocoder import async_reverse_lookup

_LOGGER = logging.getLogger(__name__)


def _entry_setting(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Read a setting from options first, then fall back to data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


def _friendly_person_name_from_entity_id(entity_id: str) -> str:
    """Return a readable person name from entity ID."""
    if "." in entity_id:
        entity_id = entity_id.split(".", 1)[1]
    return entity_id.replace("_", " ").strip().title() or entity_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    cache = hass.data[DOMAIN][entry.entry_id]["cache"]
    stats_store = hass.data[DOMAIN][entry.entry_id]["stats_store"]
    address_sensor = PersonAddressSensor(hass, entry, cache, stats_store)
    api_sensor = PersonAddressMetricSensor(address_sensor, "api_calls")
    cache_sensor = PersonAddressMetricSensor(address_sensor, "cache_hits")

    hass.data[DOMAIN][entry.entry_id]["sensor"] = address_sensor
    hass.data[DOMAIN][entry.entry_id]["metric_sensors"] = [api_sensor, cache_sensor]

    async_add_entities([address_sensor, api_sensor, cache_sensor], True)


class PersonAddressMetricSensor(SensorEntity):
    """Diagnostic metric sensor for API and cache usage."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:chart-line"

    def __init__(self, parent: "PersonAddressSensor", metric_key: str) -> None:
        self._parent = parent
        self._metric_key = metric_key
        self._attr_unique_id = f"{parent.entry.entry_id}_{metric_key}"
        self._attr_name = "API calls" if metric_key == "api_calls" else "Cache hits"

    @property
    def available(self) -> bool:
        return self._parent.available

    @property
    def native_value(self) -> int:
        return int(self._parent.stats.get(self._metric_key, 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        total = self._parent.stats.get("api_calls", 0) + self._parent.stats.get(
            "cache_hits", 0
        )
        hit_rate = (
            round((self._parent.stats.get("cache_hits", 0) / total) * 100, 2)
            if total
            else 0.0
        )
        return {
            "person_entity_id": self._parent.person_entity_id,
            "person_name": self._parent.person_name,
            "api_calls": self._parent.stats.get("api_calls", 0),
            "cache_hits": self._parent.stats.get("cache_hits", 0),
            "total_address_requests": total,
            "cache_hit_rate_percent": hit_rate,
        }

    @property
    def device_info(self) -> DeviceInfo:
        return self._parent.device_info


class PersonAddressSensor(SensorEntity):
    """Combined address sensor for a selected person entity."""

    _attr_should_poll = False
    _attr_icon = "mdi:map-marker"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cache, stats_store) -> None:
        self.hass = hass
        self.entry = entry
        self.cache = cache
        self.stats_store = stats_store

        self.person_entity_id: str = entry.data[CONF_PERSON_ENTITY_ID]
        self.fields: list[str] = list(_entry_setting(entry, CONF_FIELDS, DEFAULT_FIELDS))
        self.update_rules: list[str] = list(
            _entry_setting(entry, CONF_UPDATE_RULES, DEFAULT_UPDATE_RULES)
        )
        self.interval: int = int(_entry_setting(entry, CONF_INTERVAL, DEFAULT_INTERVAL))
        self.distance_threshold: int = int(
            _entry_setting(entry, CONF_DISTANCE_THRESHOLD, DEFAULT_DISTANCE_THRESHOLD)
        )
        self.prefer_zone: bool = bool(
            _entry_setting(entry, CONF_PREFER_ZONE, DEFAULT_PREFER_ZONE)
        )

        self._person_name = self._resolve_person_name()
        self._attr_name = f"{self._person_name} Address"
        self._attr_unique_id = f"{entry.entry_id}_combined_address"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        self._attr_available = True

        self._last_lat: float | None = None
        self._last_lon: float | None = None
        self._last_update_ts: float | None = None
        self._metric_entities: list[PersonAddressMetricSensor] = []
        self.stats: dict[str, int] = {
            "api_calls": 0,
            "cache_hits": 0,
        }

    @property
    def person_name(self) -> str:
        """Return resolved person display name."""
        return self._person_name

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
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.person_entity_id],
                self._async_handle_state_event,
            )
        )

        metric_entities = (
            self.hass.data.get(DOMAIN, {})
            .get(self.entry.entry_id, {})
            .get("metric_sensors", [])
        )
        self._metric_entities = list(metric_entities)

        self.stats = await self.stats_store.async_get(self.entry.entry_id)
        self._async_write_metric_states()

        current_state = self.hass.states.get(self.person_entity_id)
        if current_state is not None:
            self.hass.async_create_task(
                self._async_safe_process_state(current_state, force=True)
            )

    @callback
    def _async_handle_state_event(self, event) -> None:
        """Handle person state-change event."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        self.hass.async_create_task(self._async_safe_process_state(new_state))

    async def async_force_refresh(self) -> None:
        """Force an immediate refresh from current coordinates."""
        state = self.hass.states.get(self.person_entity_id)
        if state is None:
            _LOGGER.warning(
                "Force refresh skipped for %s: person state not found",
                self.person_entity_id,
            )
            return

        _LOGGER.warning("Force refresh requested for %s", self.person_entity_id)
        await self._async_safe_process_state(state, force=True)

    async def _async_safe_process_state(self, state, force: bool = False) -> None:
        """Process state safely without breaking entity lifecycle."""
        try:
            await self._async_process_state(state, force=force)
        except Exception as err:
            self._attr_available = False
            self._attr_extra_state_attributes = {
                "person_entity_id": self.person_entity_id,
                "person_name": self.person_name,
                "status": "update_failed",
                "last_error": str(err),
            }
            self.async_write_ha_state()
            self._async_write_metric_states()
            _LOGGER.exception(
                "Failed updating address sensor for %s",
                self.person_entity_id,
            )

    async def _async_process_state(self, state, force: bool = False) -> None:
        """Process current person state and update sensor."""
        lat = state.attributes.get(ATTR_LATITUDE)
        lon = state.attributes.get(ATTR_LONGITUDE)

        self._person_name = self._resolve_person_name(state)
        self._attr_name = f"{self._person_name} Address"

        if lat is None or lon is None:
            self._attr_available = True
            self._attr_native_value = None
            self._attr_extra_state_attributes = {
                "person_entity_id": self.person_entity_id,
                "person_name": self.person_name,
                "status": "no_coordinates",
            }
            self.async_write_ha_state()
            self._async_write_metric_states()
            _LOGGER.warning("No coordinates available for %s", self.person_entity_id)
            return

        now_ts = self.hass.loop.time()
        distance = None
        time_passed = True
        moved = True
        triggered_rules: list[str] = []
        enabled_rules = set(self.update_rules)

        if not force:
            if self._last_lat is not None and self._last_lon is not None:
                distance = _distance_meters(self._last_lat, self._last_lon, lat, lon)
                moved = distance >= self.distance_threshold
            if self._last_update_ts is not None:
                time_passed = (now_ts - self._last_update_ts) >= self.interval

            if "distance_threshold" in enabled_rules and moved:
                triggered_rules.append("distance_threshold")
            if "time_interval" in enabled_rules and time_passed:
                triggered_rules.append("time_interval")

            if enabled_rules and not triggered_rules:
                _LOGGER.debug(
                    (
                        "Skipping update for %s: enabled_rules=%s distance=%.2f "
                        "threshold=%s time_passed=%s interval=%s"
                    ),
                    self.person_entity_id,
                    sorted(enabled_rules),
                    distance or 0,
                    self.distance_threshold,
                    time_passed,
                    self.interval,
                )
                return

            if not enabled_rules:
                triggered_rules.append("state_change")
        else:
            triggered_rules.append("force_update")

        zone_name = None
        if self.prefer_zone:
            zone_name = _find_zone_name(self.hass, lat, lon)

        cache_key = f"{round(lat, 6)},{round(lon, 6)}"
        address_data = {} if force else (await self.cache.async_get(cache_key) or {})
        data_source = "cache" if address_data else "api"

        if address_data:
            self.stats["cache_hits"] += 1
            await self._async_persist_stats()
            _LOGGER.debug("Using cached address for %s", self.person_entity_id)

        if not address_data:
            _LOGGER.debug(
                "Reverse geocoding %s at lat=%s lon=%s",
                self.person_entity_id,
                lat,
                lon,
            )
            looked_up = await async_reverse_lookup(self.hass, lat, lon)
            self.stats["api_calls"] += 1
            await self._async_persist_stats()
            if looked_up is None:
                if zone_name:
                    address_data = {
                        "zone": zone_name,
                        "full_address": zone_name,
                    }
                    data_source = "zone_fallback"
                    _LOGGER.warning(
                        "Reverse geocoding failed for %s, falling back to zone '%s'",
                        self.person_entity_id,
                        zone_name,
                    )
                else:
                    self._attr_available = True
                    self._attr_native_value = None
                    self._attr_extra_state_attributes = {
                        "person_entity_id": self.person_entity_id,
                        "person_name": self.person_name,
                        "status": "geocode_failed",
                        "latitude": lat,
                        "longitude": lon,
                        "triggered_rules": triggered_rules,
                        "configured_update_rules": self.update_rules,
                        "api_calls": self.stats["api_calls"],
                        "cache_hits": self.stats["cache_hits"],
                    }
                    self.async_write_ha_state()
                    self._async_write_metric_states()
                    _LOGGER.warning(
                        "Reverse geocoding returned no result for %s",
                        self.person_entity_id,
                    )
                    return
            else:
                address_data = looked_up
                await self.cache.async_set(cache_key, address_data)

        if zone_name:
            address_data["zone"] = zone_name

        combined = self._format_selected_fields(address_data)
        if not combined:
            combined = (
                address_data.get("full_address") or address_data.get("zone") or None
            )

        total_requests = self.stats["api_calls"] + self.stats["cache_hits"]
        cache_hit_rate = (
            round((self.stats["cache_hits"] / total_requests) * 100, 2)
            if total_requests
            else 0.0
        )

        self._attr_available = True
        self._attr_native_value = combined
        self._attr_extra_state_attributes = {
            "person_entity_id": self.person_entity_id,
            "person_name": self.person_name,
            "selected_fields": self.fields,
            "configured_update_rules": self.update_rules,
            "triggered_rules": triggered_rules,
            "latitude": lat,
            "longitude": lon,
            "distance_from_last_update_m": (
                round(distance, 2) if distance is not None else None
            ),
            "minimum_distance_threshold_m": self.distance_threshold,
            "minimum_update_interval_s": self.interval,
            "force_update_supported": True,
            "data_source": data_source,
            "api_calls": self.stats["api_calls"],
            "cache_hits": self.stats["cache_hits"],
            "total_address_requests": total_requests,
            "cache_hit_rate_percent": cache_hit_rate,
            **address_data,
        }

        self._last_lat = lat
        self._last_lon = lon
        self._last_update_ts = now_ts

        self.async_write_ha_state()
        self._async_write_metric_states()
        _LOGGER.warning(
            "Updated %s address sensor to '%s' using %s",
            self.person_entity_id,
            self._attr_native_value,
            data_source,
        )

    def _async_write_metric_states(self) -> None:
        """Refresh linked metric entities."""
        for entity in self._metric_entities:
            if getattr(entity, "hass", None) is None:
                continue
            entity.async_write_ha_state()

    async def _async_persist_stats(self) -> None:
        """Persist API/cache counters to disk."""
        await self.stats_store.async_set(self.entry.entry_id, self.stats)

    def _resolve_person_name(self, state=None) -> str:
        """Resolve person display name with a readable fallback."""
        if state is None:
            state = self.hass.states.get(self.person_entity_id)
        if state and state.name:
            return state.name
        return _friendly_person_name_from_entity_id(self.person_entity_id)

    def _format_selected_fields(self, address_data: dict[str, Any]) -> str:
        """Build one comma-separated string from selected fields."""
        values: list[str] = []
        for field in self.fields:
            value = address_data.get(field)
            if value:
                values.append(str(value))

        if values:
            return ", ".join(values)

        return ""


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