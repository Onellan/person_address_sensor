from geopy.geocoders import Nominatim


geolocator = Nominatim(user_agent="ha_person_address_sensor")


async def reverse_lookup(hass, lat, lon):

    def lookup():

        location = geolocator.reverse(
            (lat, lon),
            addressdetails=True,
            language="en",
        )

        if not location:
            return None

        return location.raw.get("address")

    return await hass.async_add_executor_job(lookup)