from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CACHE_TTL_SECONDS


class AddressCache:
    """Async-safe persistent cache for reverse geocoding results."""

    def __init__(self, hass: HomeAssistant, cache_path: str | Path) -> None:
        self.hass = hass
        self.path = Path(cache_path)
        self._cache: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Load cache from disk."""
        if not self.path.exists():
            self._cache = {}
            return

        def _read() -> dict[str, dict[str, Any]]:
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return {}

        self._cache = await self.hass.async_add_executor_job(_read)

    async def async_save(self) -> None:
        """Save cache to disk."""

        def _write() -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._cache, ensure_ascii=False),
                encoding="utf-8",
            )

        await self.hass.async_add_executor_job(_write)

    async def async_get(self, key: str) -> dict[str, Any] | None:
        """Return cached address data if still valid."""
        item = self._cache.get(key)
        if not item:
            return None

        timestamp = item.get("_timestamp", 0)
        if time.time() - timestamp > CACHE_TTL_SECONDS:
            self._cache.pop(key, None)
            await self.async_save()
            return None

        data = dict(item)
        data.pop("_timestamp", None)
        return data

    async def async_set(self, key: str, value: dict[str, Any]) -> None:
        """Store address data in cache."""
        payload = dict(value)
        payload["_timestamp"] = time.time()
        self._cache[key] = payload
        await self.async_save()


class PersistentStatsStore:
    """Async-safe persistent store for per-entry performance counters."""

    def __init__(self, hass: HomeAssistant, stats_path: str | Path) -> None:
        self.hass = hass
        self.path = Path(stats_path)
        self._stats: dict[str, dict[str, int]] = {}

    async def async_load(self) -> None:
        """Load stats from disk."""
        if not self.path.exists():
            self._stats = {}
            return

        def _read() -> dict[str, dict[str, int]]:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {
                        str(entry_id): {
                            "api_calls": int(values.get("api_calls", 0)),
                            "cache_hits": int(values.get("cache_hits", 0)),
                        }
                        for entry_id, values in data.items()
                        if isinstance(values, dict)
                    }
            except Exception:
                pass
            return {}

        self._stats = await self.hass.async_add_executor_job(_read)

    async def async_save(self) -> None:
        """Save stats to disk."""

        def _write() -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._stats, ensure_ascii=False),
                encoding="utf-8",
            )

        await self.hass.async_add_executor_job(_write)

    async def async_get(self, entry_id: str) -> dict[str, int]:
        """Return persisted counters for one config entry."""
        values = self._stats.get(entry_id, {})
        return {
            "api_calls": int(values.get("api_calls", 0)),
            "cache_hits": int(values.get("cache_hits", 0)),
        }

    async def async_set(self, entry_id: str, stats: dict[str, int]) -> None:
        """Persist counters for one config entry."""
        self._stats[entry_id] = {
            "api_calls": int(stats.get("api_calls", 0)),
            "cache_hits": int(stats.get("cache_hits", 0)),
        }
        await self.async_save()

    async def async_remove(self, entry_id: str) -> None:
        """Remove persisted counters for one config entry."""
        if entry_id in self._stats:
            self._stats.pop(entry_id, None)
            await self.async_save()
