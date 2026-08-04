"""
LI-COR API Connectivity and Discovery Test

Validates communication with the LI-COR Cloud API by:

    - Verifying API authentication
    - Retrieving available devices
    - Inspecting device metadata
    - Inspecting sensor metadata
    - Testing historical data endpoint access
    - Displaying API response structures

Purpose:
    - Confirm API credentials are working
    - Verify device visibility
    - Assist troubleshooting and development of
      licor_to_labguru.py

Note:
    This script does not create Labguru datasets or
    upload records. It is intended solely for API
    validation and response inspection.
"""
import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

from licor.licor_to_labguru import LicorClient


client = LicorClient()

print("=" * 80)
print("TEST 1: GET DEVICES")
print("=" * 80)

devices = client.get_devices()

print(json.dumps(devices, indent=2, default=str))

print("\n")
print("=" * 80)
print("TEST 2: GET DATA")
print("\n")
print("=" * 80)
print("TEST 2: GET DATA")
print("=" * 80)

first_device = devices["devices"][0]

device_serial = first_device[
    "deviceSerialNumber"
]

first_sensor = first_device[
    "sensors"
][0]

sensor_serial = first_sensor[
    "sensorSerialNumber"
]

print(
    f"Testing device: {device_serial}"
)

print(
    f"Testing sensor: {sensor_serial}"
)

from datetime import datetime
from datetime import timezone
from datetime import timedelta

end_time = int(
    datetime.now(
        timezone.utc
    ).timestamp() * 1000
)

start_time = int(
    (
        datetime.now(timezone.utc)
        - timedelta(days=30)
    ).timestamp() * 1000
)

print("Start:", start_time)
print("End:", end_time)

data = client.get_data(
    device_serial_number=device_serial,
    sensor_serial_number=sensor_serial,
    start_time=start_time,
    end_time=end_time
)

print(
    json.dumps(
        data,
        indent=2,
        default=str
    )
)

print("\n")
print("=" * 80)
print("DEVICE DETAIL")
print("=" * 80)

print(
    json.dumps(
        first_device,
        indent=2,
        default=str
    )
)