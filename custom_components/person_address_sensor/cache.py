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
        self._load_cache()

    def _load_cache(self):
        if self.path.exists():
            try:
                self.cache = json.loads(self.path.read_text())
            except Exception as e:
                _LOGGER.warning("Failed to load cache: %s", e)
                self.cache = {}

    async def set(self, key, value):
        """Set cache value async-safe."""
        self.cache[key] = (value, int(self.hass.loop.time()))
        await self.hass.async_add_executor_job(self._write_cache_to_disk)

    def get(self, key):
        entry = self.cache.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if self.hass.loop.time() - timestamp > CACHE_TIMEOUT:
            return None
        return value

    def _write_cache_to_disk(self):
        try:
            self.path.write_text(json.dumps(self.cache))
        except Exception as e:
            _LOGGER.warning("Failed to write cache: %s", e)