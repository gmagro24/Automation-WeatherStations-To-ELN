"""
WeatherLink Station and Sensor Inspection Test

Retrieves all WeatherLink stations, current sensor blocks,
and sensor metadata for API validation and troubleshooting.

Purpose:
    - Verify WeatherLink API authentication
    - Inspect station configuration
    - Inspect sensor block structures
    - Compare current conditions with sensor metadata
    - Assist development of Labguru dataset mappings

Output:
    - Station information
    - Current sensor blocks
    - Sensor metadata examples
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from config import WEATHERLINK_API_KEY, WEATHERLINK_API_SECRET
import json

from weatherLink.weatherlink_to_labguru import WeatherLinkClient

client = WeatherLinkClient(
    WEATHERLINK_API_KEY,
    WEATHERLINK_API_SECRET
)

stations = client.get_stations()

for station in stations:

    station_name = station.get("station_name")
    station_id = station.get("station_id")

    print("\n" + "=" * 60)
    print(f"STATION: {station_name}")
    print(f"STATION ID: {station_id}")

    current = client.get_current_conditions(station_id)

    for sensor in current.get("sensors", []):

        print("\nSENSOR BLOCK")
        print(json.dumps(sensor, indent=2))



print(
    "\n" + "=" * 60
)
sensors = client.get_sensors()

import json

print(json.dumps(sensors[:5], indent=2))