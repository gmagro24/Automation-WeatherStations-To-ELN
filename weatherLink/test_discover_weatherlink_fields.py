"""
WeatherLink Field Discovery Test

Retrieves all WeatherLink stations and current sensor data,
then scans every sensor packet to identify available data
fields returned by the WeatherLink API.

Purpose:
    - Discover available WeatherLink measurements
    - Validate API connectivity
    - Assist dataset schema design
    - Identify new fields for Labguru integration

Output:
    Prints a sorted list of all unique data fields found
    across all stations and sensors.
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from config import WEATHERLINK_API_KEY, WEATHERLINK_API_SECRET
from weatherLink.weatherlink_to_labguru import WeatherLinkClient

client = WeatherLinkClient(
    WEATHERLINK_API_KEY,
    WEATHERLINK_API_SECRET
)

stations = client.get_stations()

all_fields = set()

for station in stations:

    current_data = client.get_current_conditions(
        station["station_id"]
    )

    for sensor in current_data.get("sensors", []):

        for packet in sensor.get("data", []):

            all_fields.update(packet.keys())

for field in sorted(all_fields):
    print(field)