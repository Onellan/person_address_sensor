import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_state_change
from .cache import AddressCache
from .geocoder import reverse_lookup
from .const import DOMAIN, CACHE_FILE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    person = entry.data["person"]
    fields = entry.data.get("fields", ["full_address"])
    interval = entry.data.get("interval", 300)

    cache_path = hass.config.path(CACHE_FILE)
    cache = AddressCache(cache_path, hass)
    await cache.load()

    async_add_entities([PersonAddressSensor(hass, person, fields, cache, interval)], True)

class PersonAddressSensor(SensorEntity):
    def __init__(self, hass, person_entity_id, fields, cache, interval):
        self.hass = hass
        self.entity_id_person = person_entity_id
        self.fields = fields
        self.cache = cache
        self._attr_name = f"{person_entity_id.split('.')[-1]}_address"
        self._attr_unique_id = f"{person_entity_id}_address"
        self._interval = interval
        self._state = None

    async def async_added_to_hass(self):
        state = self.hass.states.get(self.entity_id_person)
        await self._update_from_state(state)
        async_track_state_change(self.hass, self.entity_id_person, self._update_from_state)

    async def _update_from_state(self, entity, old_state=None, new_state=None):
        state_obj = new_state or entity
        if not state_obj:
            return

        lat = getattr(state_obj, "attributes", {}).get("latitude")
        lon = getattr(state_obj, "attributes", {}).get("longitude")
        if lat is None or lon is None:
            return

        key = f"{lat},{lon}"
        address_data = self.cache.get(key)
        if not address_data:
            address_data = await reverse_lookup(lat, lon)
            if address_data:
                await self.cache.set(key, address_data)

        if address_data:
            attr = address_data.get("address", {})
            values = [attr.get(f, "") for f in self.fields]
            self._state = ", ".join([v for v in values if v])
            self.async_write_ha_state()

    @property
    def native_value(self):
        return self._state