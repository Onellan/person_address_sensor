# __init__.py
from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .cache import AddressCache
from .const import CACHE_FILE, DOMAIN

PLATFORMS: list[str] = ["sensor", "button"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    cache = AddressCache(hass, Path(hass.config.path(CACHE_FILE)))
    await cache.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "cache": cache,
        "sensor": None,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_reload_entry(
        updated_hass: HomeAssistant, updated_entry: ConfigEntry
    ) -> None:
        await updated_hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok