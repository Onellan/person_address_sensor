import json
import time
from pathlib import Path

class AddressCache:

    def __init__(self, path, hass=None):
        self.path = Path(path)
        self.cache = {}
        self.hass = hass
        self.load()

    def load(self):
        if self.path.exists():
            self.cache = json.loads(self.path.read_text())

    async def save(self):
        if self.hass:
            await self.hass.async_add_executor_job(self.path.write_text, json.dumps(self.cache))
        else:
            self.path.write_text(json.dumps(self.cache))

    async def get(self, key):
        entry = self.cache.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if time.time() - timestamp > 86400:
            return None
        return value

    async def set(self, key, value):
        self.cache[key] = (value, time.time())
        await self.save()