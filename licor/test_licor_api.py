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
import requests
import logging
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

from licor.licor_to_labguru import (
    LicorClient,
    extract_devices,
    format_licor_datetime,
)

licor_logger = logging.getLogger("licor.licor_to_labguru")


client = LicorClient()

print("=" * 80)
print("TEST 1: GET DEVICES")
print("=" * 80)

devices_response = client.get_devices()

devices = extract_devices(devices_response)

print(json.dumps(devices_response, indent=2, default=str))

print("\n")
print("=" * 80)
print("TEST 2: GET DATA")
print("=" * 80)

if not devices:
    raise RuntimeError("No LI-COR devices found for this account.")

first_device = devices[0]

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


end_time = format_licor_datetime(
    datetime.now(timezone.utc)
)

start_time = format_licor_datetime(
    datetime.now(timezone.utc)
    - timedelta(days=30)
)

print("Start:", start_time)
print("End:", end_time)

previous_level = licor_logger.level

try:
    # /v1/data 403 is common when token lacks historical scope.
    # Silence client error logs here so test output stays readable.
    licor_logger.setLevel(logging.CRITICAL)

    data = client.get_newa_data(
        device_serial_number=device_serial,
        start_date_time=start_time,
        end_date_time=end_time
    )
except requests.HTTPError as error:
    response = error.response

    if response is not None and response.status_code == 403:
        print("WARNING: LI-COR /v1/data endpoint returned 403 Forbidden.")
        print(
            "Your token can list devices but does not have historical data scope."
        )
        print("Requested URL:", response.url)
        print("Response body:", response.text)
        data = {
            "error": "403 Forbidden from /v1/data endpoint",
            "url": response.url,
            "response": response.text,
        }
    else:
        raise
finally:
    licor_logger.setLevel(previous_level)

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