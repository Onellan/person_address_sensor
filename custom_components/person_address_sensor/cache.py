import json
import time
from pathlib import Path


class AddressCache:

    def __init__(self, path):
        self.path = Path(path)
        self.cache = {}
        self.load()

    def load(self):
        if self.path.exists():
            self.cache = json.loads(self.path.read_text())

    def save(self):
        self.path.write_text(json.dumps(self.cache))

    def get(self, key):

        entry = self.cache.get(key)

        if not entry:
            return None

        value, timestamp = entry

        if time.time() - timestamp > 86400:
            return None

        return value

    def set(self, key, value):

        self.cache[key] = (value, time.time())

        self.save()