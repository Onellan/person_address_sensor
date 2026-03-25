from __future__ import annotations

from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession


async def async_reverse_lookup(hass, lat: float, lon: float) -> dict[str, Any] | None:
    """Reverse geocode coordinates using Nominatim."""
    session = async_get_clientsession(hass)
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "jsonv2",
        "lat": lat,
        "lon": lon,
        "addressdetails": 1,
        "accept-language": "en",
    }
    headers = {
        "User-Agent": "HomeAssistantPersonAddressSensor/6.0.0"
    }

    async with session.get(url, params=params, headers=headers, timeout=15) as resp:
        if resp.status != 200:
            return None

        payload = await resp.json()

    address = payload.get("address", {})
    display_name = payload.get("display_name")

    return {
        "full_address": display_name,
        "house_number": address.get("house_number"),
        "road": address.get("road") or address.get("pedestrian"),
        "suburb": address.get("suburb") or address.get("residential"),
        "neighbourhood": address.get("neighbourhood") or address.get("quarter"),
        "city": address.get("city") or address.get("town") or address.get("village") or address.get("municipality"),
        "county": address.get("county"),
        "state": address.get("state") or address.get("province"),
        "postcode": address.get("postcode"),
        "country": address.get("country"),
        "country_code": address.get("country_code").upper() if address.get("country_code") else None,
        "zone": None,
    }