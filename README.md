# Person Address Sensor

A Home Assistant custom integration that creates one combined address sensor for a selected `person` entity.

## Features

- Select a person from a dropdown
- Select which address fields to show
- One combined sensor with comma-separated fields
- Immediate population from the person's current location
- Country-aware reverse geocoding
- Optional Home Assistant zone fallback
- Minimum update interval
- Minimum movement threshold
- Editable later through the integration options

## Installation with HACS

1. Push this repository to GitHub
2. In HACS, add it as a **Custom repository**
3. Category: **Integration**
4. Install **Person Address Sensor**
5. Restart Home Assistant
6. Add the integration from **Settings > Devices & Services**

## Example output

Depending on your selected fields:

- `Oxford Road, Rosebank, Johannesburg, Gauteng, South Africa`
- `Home`
- `Johannesburg, Gauteng`