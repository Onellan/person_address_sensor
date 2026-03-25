from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN


async def async_setup(hass: HomeAssistant, config: dict):

    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        hass.data[DOMAIN]["yaml"] = config[DOMAIN]

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):

    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):

    if config_entry.version == 1:
        config_entry.version = 2

    return True