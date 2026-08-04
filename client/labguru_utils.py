"""
Labguru Utility Functions

Shared helper functions used across WeatherLink and LI-COR
integrations for safe data extraction and standard dataset
schema generation.
"""

def safe_get(obj, keys, default=""):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        value = obj.get(key)

        if value not in [None, ""]:
            return value

    return default


def build_base_columns():
    return [
        "record_timestamp",
        "station_name",
        "station_id",
        "device_name",
        "sensor_id",
        "source_record_key",
        "weatherlink_archival_interval",
        "weatherlink_timezone_offset",
        "sync_created_at",
        "raw_json",
    ]