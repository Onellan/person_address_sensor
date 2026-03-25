import json
import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)
CACHE_TIMEOUT = 3600  # seconds


class AddressCache:
    """Async-safe persistent cache."""

    def __init__(self, path: Path, hass):
        self.path = path
        self.hass = hass
        self.cache = {}

    async def load(self):
        """Load cache async-safe."""
        if self.path.exists():
            def _read():
                try:
                    return json.loads(self.path.read_text())
                except Exception as e:
                    _LOGGER.warning("Failed to read cache: %s", e)
                    return {}
            self.cache = await self.hass.async_add_executor_job(_read)

    async def save(self):
        """Save cache async-safe."""
        def _write():
            try:
                self.path.write_text(json.dumps(self.cache))
            except Exception as e:
                _LOGGER.warning("Failed to write cache: %s", e)
        await self.hass.async_add_executor_job(_write)

    async def set(self, key, value):
        self.cache[key] = (value, int(self.hass.loop.time()))
        await self.save()

    def get(self, key):
        entry = self.cache.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if self.hass.loop.time() - timestamp > CACHE_TIMEOUT:
            return None
        return value