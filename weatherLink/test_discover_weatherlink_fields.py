# test_discover_weatherlink_fields.py
from config import WEATHERLINK_API_KEY, WEATHERLINK_API_SECRET
from weatherlink_to_labguru import WeatherLinkClient

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