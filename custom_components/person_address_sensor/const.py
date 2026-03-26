from __future__ import annotations

DOMAIN = "person_address_sensor"

CONF_PERSON_ENTITY_ID = "person_entity_id"
CONF_FIELDS = "fields"
CONF_INTERVAL = "interval"
CONF_DISTANCE_THRESHOLD = "distance_threshold"
CONF_PREFER_ZONE = "prefer_zone"
CONF_UPDATE_RULES = "update_rules"

DEFAULT_FIELDS: list[str] = ["road", "suburb", "city", "state", "country"]
DEFAULT_INTERVAL = 300
DEFAULT_DISTANCE_THRESHOLD = 50
DEFAULT_PREFER_ZONE = True
DEFAULT_UPDATE_RULES: list[str] = ["time_interval", "distance_threshold"]

CACHE_FILE = "person_address_cache.json"
CACHE_TTL_SECONDS = 86400

FIELD_OPTIONS: list[str] = [
    "full_address",
    "house_number",
    "road",
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

FIELD_LABELS: dict[str, str] = {
    "full_address": "Full address",
    "house_number": "House number",
    "road": "Road / street",
    "suburb": "Suburb",
    "neighbourhood": "Neighbourhood",
    "city": "City / town",
    "county": "County",
    "state": "State / province",
    "postcode": "Postcode",
    "country": "Country",
    "country_code": "Country code",
    "zone": "Home Assistant zone",
}

UPDATE_RULE_OPTIONS: list[str] = [
    "time_interval",
    "distance_threshold",
]

UPDATE_RULE_LABELS: dict[str, str] = {
    "time_interval": "Update when minimum time interval has passed",
    "distance_threshold": "Update when minimum movement distance is reached",
}

STATS_FILE = "person_address_stats.json"
