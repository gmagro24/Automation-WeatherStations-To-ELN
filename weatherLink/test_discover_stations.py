from config import WEATHERLINK_API_KEY, WEATHERLINK_API_SECRET
from client.labguru_client import LabguruClient
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