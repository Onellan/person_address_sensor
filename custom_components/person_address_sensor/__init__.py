# __init__.py
from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .cache import AddressCache, PersistentStatsStore
from .const import CACHE_FILE, DOMAIN, STATS_FILE

PLATFORMS: list[str] = ["sensor", "button"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    cache = domain_data.get("cache")
    if cache is None:
        cache = AddressCache(hass, Path(hass.config.path(CACHE_FILE)))
        await cache.async_load()
        domain_data["cache"] = cache

    stats_store = domain_data.get("stats_store")
    if stats_store is None:
        stats_store = PersistentStatsStore(hass, Path(hass.config.path(STATS_FILE)))
        await stats_store.async_load()
        domain_data["stats_store"] = stats_store

    domain_data[entry.entry_id] = {
        "cache": cache,
        "stats_store": stats_store,
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