import logging
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt

from homeassistant.helpers.entity import SensorEntity
from homeassistant.helpers.event import async_track_state_change
from homeassistant.components.zone import async_active_zone

from .const import DEFAULT_INTERVAL, MINIMUM_INTERVAL
from .cache import AddressCache
from .geocoder import reverse_lookup

_LOGGER = logging.getLogger(__name__)


class PersonAddressSensor(SensorEntity):

    def __init__(self, hass, config, cache):

        self.hass = hass

        self.person = config["person"]

        self.interval = max(
            config.get("interval", DEFAULT_INTERVAL),
            MINIMUM_INTERVAL
        )

        self.template = config.get("format_template")
        self.distance_threshold = config.get("distance_threshold", 50)

        self.last_lat = None
        self.last_lon = None

        self.cache = cache

        self.last_update = None

        self._attr_name = f"{self.person}_address"


    async def async_added_to_hass(self):

        async_track_state_change(
            self.hass,
            self.person,
            self._state_changed
        )


    async def _state_changed(self, entity, old_state, new_state):

        if not new_state:
            return

        lat = new_state.attributes.get("latitude")
        lon = new_state.attributes.get("longitude")

        if lat is None:
            return

        # Distance filtering (GPS jitter protection)
        if self.last_lat and self.last_lon:

            distance = self._distance_meters(
                self.last_lat,
                self.last_lon,
        return r * c
