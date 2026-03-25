import logging
from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

async def reverse_lookup(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&addressdetails=1"
    try:
        async with ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "HomeAssistantPersonAddress/1.0"}) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Failed reverse geocode HTTP %s", resp.status)
                    return None
                return await resp.json()
    except Exception as e:
        _LOGGER.warning("Reverse geocode error: %s", e)
        return None