import logging
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

from homeassistant.helpers.entity import SensorEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.zone import async_active_zone

from .const import (
    DOMAIN,
    DEFAULT_INTERVAL,
    DEFAULT_DISTANCE_THRESHOLD,
)

from .cache import AddressCache
from .geocoder import reverse_lookup

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):

    yaml_config = hass.data.get(DOMAIN, {}).get("yaml")

    sensors = []

    if yaml_config:

        cache_path = Path(hass.config.path("person_address_cache.json"))

        cache = AddressCache(cache_path)

        for person in yaml_config.get("persons", []):

            sensors.append(PersonAddressSensor(hass, person, cache))

    async_add_entities(sensors)


class PersonAddressSensor(SensorEntity):

    def __init__(self, hass, config, cache):

        self.hass = hass
        self.person = config["person"]
        self.interval = config.get("interval", DEFAULT_INTERVAL)
        self.distance_threshold = config.get("distance_threshold", DEFAULT_DISTANCE_THRESHOLD)
        self.template = config.get("format_template")
        self.cache = cache

        self.last_update = None
        self.last_lat = None
        self.last_lon = None

        self._attr_name = f"{self.person}_address"

    async def async_added_to_hass(self):

        async_track_state_change_event(
            self.hass,
            [self.person],
            self._state_changed
        )
        return r * c