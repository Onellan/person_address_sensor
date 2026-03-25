from __future__ import annotations

DOMAIN = "person_address_sensor"

CONF_PERSON_ENTITY_ID = "person_entity_id"
CONF_FIELDS = "fields"
CONF_INTERVAL = "interval"
CONF_DISTANCE_THRESHOLD = "distance_threshold"
CONF_PREFER_ZONE = "prefer_zone"

DEFAULT_FIELDS: list[str] = ["road", "suburb", "city", "state", "country"]
DEFAULT_INTERVAL = 300
DEFAULT_DISTANCE_THRESHOLD = 50
DEFAULT_PREFER_ZONE = True

CACHE_FILE = "person_address_cache.json"
CACHE_TTL_SECONDS = 86400

FIELD_OPTIONS: list[str] = [
    "full_address",
    "road",
    "house_number",
    "suburb",
    "neighbourhood",
    "city",
    "county",
    "state",
    "postcode",
    "country",
    "country_code",
    "zone",
]