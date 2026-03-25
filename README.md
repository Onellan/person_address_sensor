# Person Address Sensor Pro

Upstream‑quality Home Assistant integration with GPS jitter filtering and movement distance threshold support.

## Features

- Movement triggered updates
- Persistent cache
- Zone fallback
- YAML configuration
- Template formatting
- Device tracker fallback
- Address component parsing ready

## YAML Example

person_address_sensor:

  persons:

    - person: person.onellan
      interval: 300
      format_template: "📍 {address}"
