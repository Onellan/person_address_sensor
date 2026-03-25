import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.zone import async_active_zone

from .const import DEFAULT_INTERVAL, CACHE_TIMEOUT
from .geocoder import reverse_lookup

_LOGGER = logging.getLogger(__name__)


class AddressCache:
    """Async-safe persistent cache."""

    def __init__(self, path: Path, hass):
        self.path = path
        self.hass = hass
        self.cache = {}
        self._load_cache()

    def _load_cache(self):
        if self.path.exists():
            try:
                self.cache = json.loads(self.path.read_text())
            except Exception as e:
                _LOGGER.warning("Failed to load cache: %s", e)
                self.cache = {}

    async def set(self, key, value):
        """Set cache value async-safe."""
        self.cache[key] = (value, int(time.time()))
        await self.hass.async_add_executor_job(self._write_cache_to_disk)

    def get(self, key):
        entry = self.cache.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if time.time() - timestamp > CACHE_TIMEOUT:
            return None
        return value

    def _write_cache_to_disk(self):
        try:
            self.path.write_text(json.dumps(self.cache))
        except Exception as e:
            _LOGGER.warning("Failed to write cache: %s", e)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor for the selected person."""
    cache_path = Path(hass.config.path("person_address_cache.json"))
    cache = AddressCache(cache_path, hass)

    sensor = PersonAddressSensor(
        hass,
        entry.data["person"],
        entry.data.get("fields", ["full_address"]),
        entry.data.get("interval", DEFAULT_INTERVAL),
        cache,
    )
    async_add_entities([sensor], True)


class PersonAddressSensor(SensorEntity):
    """Single sensor showing all selected fields for a person."""

    def __init__(self, hass, person, fields, interval, cache):
        self.hass = hass
        self.person = person
        self.fields = fields
        self.interval = max(interval, DEFAULT_INTERVAL)
        self.cache = cache
        self.last_update = None
        self.last_lat = None
        self.last_lon = None
        self._attr_name = f"{self.person}_address"
        self._attr_native_value = None

    async def async_added_to_hass(self):
        """Track person state changes."""
        state = self.hass.states.get(self.person)
        if state:
            await self._update_from_state(state)

        async_track_state_change_event(
            self.hass,
            [self.person],
            self._update_from_state
        )

    async def _update_from_state(self, event):
        """Handle person state changes."""
        new_state = event.data.get("new_state")
        if not new_state:
            return

        lat = new_state.attributes.get("latitude")
        lon = new_state.attributes.get("longitude")

        # Skip if location not available
        if lat is None or lon is None:
            return

        # Skip if same coordinates
        if lat == self.last_lat and lon == self.last_lon:
            return

        # Skip if interval not passed
        if self.last_update and datetime.now() - self.last_update < timedelta(seconds=self.interval):
            return

        self.last_lat = lat
        self.last_lon = lon
        self.last_update = datetime.now()

        await self._update_address(lat, lon)

    async def _update_address(self, lat, lon):
        """Resolve address and update sensor."""
        # Check if inside a known HA zone
        zone = async_active_zone(self.hass, lat, lon)
        if zone:
            address_dict = {"zone": zone.name}
        else:
            key = f"{lat},{lon}"
            cached = self.cache.get(key)
            if cached:
                address_dict = cached
            else:
                location = await reverse_lookup(self.hass, lat, lon)
                if location is None:
                    return
                # Parse into country-aware components
                address_dict = self._parse_address(location.raw.get("address", {}))
                await self.cache.set(key, address_dict)

        # Format selected fields
        formatted = self._format_fields(address_dict)
        if formatted != self._attr_native_value:
            self._attr_native_value = formatted
            self.async_write_ha_state()

    def _parse_address(self, addr):
        """Return dict of all relevant fields."""
        return {
            "road": addr.get("road") or addr.get("pedestrian") or "",
            "suburb": addr.get("suburb") or addr.get("neighbourhood") or "",
            "city": addr.get("city") or addr.get("town") or addr.get("village") or "",
            "municipality": addr.get("municipality") or "",
            "county": addr.get("county") or "",
            "state": addr.get("state") or "",
            "postcode": addr.get("postcode") or "",
            "country": addr.get("country") or "",
            "country_code": addr.get("country_code") or "",
            "zone": addr.get("zone") or "",
        }

    def _format_fields(self, addr_dict):
        """Return all selected fields joined by commas."""
        return ", ".join(addr_dict.get(f, "") for f in self.fields if addr_dict.get(f))