from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="ha_person_address_sensor")


async def reverse_lookup(hass, lat, lon):

    def lookup():
        location = geolocator.reverse((lat, lon))
        return location.address if location else None

    return await hass.async_add_executor_job(lookup)
