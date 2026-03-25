async def async_get_config_entry_diagnostics(hass, entry):

    return {
        "entry_data": entry.data,
        "version": entry.version,
    }