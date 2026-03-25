import logging
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.zone import async_active_zone

from .cache import AddressCache
from .geocoder import reverse_lookup
from .const import DEFAULT_DISTANCE_THRESHOLD


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):

    cache_path = Path(hass.config.path("person_address_cache.json"))
    cache = AddressCache(cache_path)

    sensor = PersonAddressSensor(
        hass,
        entry.data["person"],
        entry.data["fields"],
        entry.data["interval"],
        cache,
    )

    async_add_entities([sensor], True)


class PersonAddressSensor(SensorEntity):

    def __init__(self, hass, person, fields, interval, cache):

        self.hass = hass
        self.person = person
        self.fields = fields
        self.interval = interval
        self.cache = cache

        self.last_update = None
        self.last_lat = None
        self.last_lon = None

        self._attr_name = f"{person.replace('.', '_')}_address"
        self._attr_native_value = None


    async def async_added_to_hass(self):

        state = self.hass.states.get(self.person)

        if state:
            await self._update_from_state(state)

        async_track_state_change_event(
            self.hass,
            [self.person],
            self._handle_state_change
        )


    async def _handle_state_change(self, event):

        new_state = event.data.get("new_state")

        if new_state:
            await self._update_from_state(new_state)


    async def _update_from_state(self, state):

        lat = state.attributes.get("latitude")
        lon = state.attributes.get("longitude")

        if lat is None or lon is None:
            return


        if self.last_lat and self.last_lon:

            if self._distance(
                self.last_lat,
                self.last_lon,
                lat,
                lon
            ) < DEFAULT_DISTANCE_THRESHOLD:
                return


        if self.last_update:

            if datetime.now() - self.last_update < timedelta(seconds=self.interval):
                return


        zone = async_active_zone(self.hass, lat, lon)


        if zone and "zone" in self.fields:

            formatted = zone.name


        else:

            key = f"{lat},{lon}"

            cached = self.cache.get(key)


            if cached:

                address_data = cached

            else:

                address_data = await reverse_lookup(
                    self.hass,
                    lat,
                    lon,
                )

                if not address_data:
                    return

                self.cache.set(key, address_data)


            formatted = self._format_selected_fields(address_data)


        self._attr_native_value = formatted

        self.last_update = datetime.now()
        self.last_lat = lat
        self.last_lon = lon

        self.async_write_ha_state()


    def _format_selected_fields(self, address):

        components = []

        field_map = {

            "street":
                address.get("road"),

            "suburb":
                address.get("suburb")
                or address.get("neighbourhood")
                or address.get("residential"),

            "city":
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("municipality"),

            "province":
                address.get("state")
                or address.get("province"),

            "postcode":
                address.get("postcode"),

            "country":
                address.get("country"),

            "full_address":
                address.get("road"),

        }


        for field in self.fields:

            value = field_map.get(field)

            if value:
                components.append(value)


        return ", ".join(components)


    def _distance(self, lat1, lon1, lat2, lon2):

        r = 6371000

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2

        c = 2 * asin(sqrt(a))

        return r * c