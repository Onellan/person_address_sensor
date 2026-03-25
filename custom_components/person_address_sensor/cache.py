"""Async-safe cache handler."""
import json
from pathlib import Path


class AddressCache:
    def __init__(self, cache_path, hass):
        self.hass = hass
        self.path = Path(cache_path)
        self.cache = {}

    async def load(self):
        """Load cache async-safe."""
        if self.path.exists():
            data = await self.hass.async_add_executor_job(self.path.read_text)
            self.cache = json.loads(data)
        else:
            self.cache = {}

    async def save(self):
        """Save cache async-safe."""
        await self.hass.async_add_executor_job(
            self.path.write_text, json.dumps(self.cache)
        )