"""Person Address Sensor integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "person_address_sensor"


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up sensor from a config entry."""
    # Import inside async to avoid blocking event loop
    from . import sensor

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True