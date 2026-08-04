"""
WeatherLink → Labguru Synchronization

Automatically discovers WeatherLink stations and sensors,
creates or updates Labguru datasets, uploads current sensor
data, and records synchronization state.

State Tracking:
    state/sync_state.json

Author: Gina Magro
"""


import os
import re
import sys
import json
import logging
import requests

from pathlib import Path
from datetime import datetime, timezone
from client.state_manager import (load_state,save_state,utc_now)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass


try:
    import config as app_config
except Exception:
    app_config = None


def get_setting(name, default=""):
    value = os.getenv(name)

    if value not in [None, ""]:
        return value

    if app_config is not None and hasattr(app_config, name):
        value = getattr(app_config, name)

        if value not in [None, ""]:
            return value

    return default


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


WEATHERLINK_BASE_URL = "https://api.weatherlink.com/v2"

WEATHERLINK_API_KEY = get_setting("WEATHERLINK_API_KEY", "")
WEATHERLINK_API_SECRET = get_setting("WEATHERLINK_API_SECRET", "")

LABGURU_BASE_URL = get_setting("LABGURU_BASE_URL", "").rstrip("/")
LABGURU_TOKEN = get_setting("LABGURU_TOKEN", "")
LABGURU_AUTH_MODE = get_setting("LABGURU_AUTH_MODE", "bearer").lower()

LABGURU_WEATHERLINK_PARENT_FOLDER_ID = get_setting(
    "LABGURU_WEATHERLINK_PARENT_FOLDER_ID",
    ""
)

LABGURU_DATASETS_PATH = get_setting(
    "LABGURU_DATASETS_PATH",
    "/api/v1/datasets"
)

LABGURU_DATASET_DETAIL_PATH_TEMPLATE = get_setting(
    "LABGURU_DATASET_DETAIL_PATH_TEMPLATE",
    "/api/v1/datasets/{dataset_id}"
)

LABGURU_VECTOR_CREATE_PATH_TEMPLATE = get_setting(
    "LABGURU_VECTOR_CREATE_PATH_TEMPLATE",
    "/api/v1/datasets/{dataset_id}/vectors"
)

DRY_RUN = str(
    get_setting("DRY_RUN", "true")
).lower() == "true"

AUTO_ADD_COLUMNS = str(
    get_setting("AUTO_ADD_COLUMNS", "true")
).lower() == "true"

SOURCE_NAME = "WeatherLink"

SKIP_CATEGORIES = {
    "HEALTH"
}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_name(value):
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\-\(\)\[\]\.\/&]", "", text)
    return text


def clean_dataset_name(value):
    return clean_name(value)[:180]


def safe_get(obj, keys, default=""):
    if not isinstance(obj, dict):
        return default

    for key in keys:
        value = obj.get(key)

        if value not in [None, ""]:
            return value

    return default


def is_scalar(value):
    return value is None or isinstance(
        value,
        (
            str,
            int,
            float,
            bool
        )
    )


def safe_value(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def build_base_columns():
    return [
        "record_timestamp",
        "station_name",
        "station_id",
        "station_uuid",
        "station_time_zone",
        "station_city",
        "station_region",
        "station_country",
        "station_latitude",
        "station_longitude",
        "station_elevation",
        "device_name",
        "device_category",
        "sensor_id",
        "sensor_type",
        "data_structure_type",
        "source",
        "source_record_key",
        "sync_created_at",
        "raw_json"
    ]


def require_weatherlink_env():
    missing = []

    if not WEATHERLINK_API_KEY:
        missing.append("WEATHERLINK_API_KEY")

    if not WEATHERLINK_API_SECRET:
        missing.append("WEATHERLINK_API_SECRET")

    if missing:
        raise RuntimeError(
            "Missing required WeatherLink environment variables: "
            + ", ".join(missing)
        )


def require_labguru_env():
    missing = []

    if not LABGURU_BASE_URL and not DRY_RUN:
        missing.append("LABGURU_BASE_URL")

    if not LABGURU_TOKEN and not DRY_RUN:
        missing.append("LABGURU_TOKEN")

    if missing:
        raise RuntimeError(
            "Missing required Labguru environment variables: "
            + ", ".join(missing)
        )


class WeatherLinkClient:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()

    def get(self, path, params=None):
        if params is None:
            params = {}

        params["api-key"] = self.api_key

        url = f"{WEATHERLINK_BASE_URL}{path}"

        headers = {
            "X-Api-Secret": self.api_secret
        }

        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=60
        )

        if response.status_code >= 400:
            logger.error("WeatherLink request failed.")
            logger.error("URL: %s", url)
            logger.error("Status code: %s", response.status_code)

            try:
                logger.error(
                    json.dumps(
                        response.json(),
                        indent=2
                    )
                )
            except Exception:
                logger.error(response.text)

        response.raise_for_status()
        return response.json()

    def get_stations(self):
        data = self.get("/stations")
        return data.get("stations", [])

    def get_sensors(self):
        data = self.get("/sensors")
        return data.get("sensors", [])

    def get_current_conditions(self, station_id):
        return self.get(f"/current/{station_id}")


def get_station_id(station):
    return safe_get(
        station,
        [
            "station_id",
            "id"
        ],
        default=None
    )


def get_station_name(station):
    station_id = get_station_id(station)

    return str(
        safe_get(
            station,
            [
                "station_name",
                "name",
                "nickname"
            ],
            default=f"Station {station_id}"
        )
    )


def build_sensor_lookup(sensors):
    lookup = {}

    for sensor in sensors:
        lsid = safe_get(
            sensor,
            [
                "lsid",
                "sensor_id",
                "id"
            ],
            default=None
        )

        if lsid is not None:
            lookup[str(lsid)] = sensor

    return lookup


def get_sensor_id(sensor_block):
    return str(
        safe_get(
            sensor_block,
            [
                "lsid",
                "sensor_id",
                "id"
            ],
            default="unknown"
        )
    )


def get_device_name(sensor_meta, sensor_id):
    return str(
        safe_get(
            sensor_meta,
            [
                "product_name",
                "sensor_name",
                "name",
                "category",
                "sensor_type",
                "product_number"
            ],
            default=f"WeatherLink Sensor {sensor_id}"
        )
    )


def get_device_category(sensor_meta):
    return str(
        safe_get(
            sensor_meta,
            [
                "category"
            ],
            default=""
        )
    )


def build_dataset_name(station_name, sensor_meta, sensor_id):
    product_name = get_device_name(
        sensor_meta,
        sensor_id
    )

    return clean_dataset_name(
        f"{station_name} - {product_name} - {sensor_id}"
    )


def extract_sensor_blocks(current_payload):
    sensors = current_payload.get("sensors", [])

    if isinstance(sensors, list):
        return [
            sensor
            for sensor in sensors
            if isinstance(sensor, dict)
        ]

    return []


def extract_data_packets(sensor_block):
    data = sensor_block.get("data", [])

    if isinstance(data, list):
        return [
            packet
            for packet in data
            if isinstance(packet, dict)
        ]

    if isinstance(data, dict):
        return [data]

    return []


def discover_columns_from_packets(data_packets):
    columns = build_base_columns()

    for packet in data_packets:
        for field_key, value in packet.items():
            if not is_scalar(value):
                continue

            if field_key not in columns:
                columns.append(field_key)

    return columns


def build_station_metadata(station):
    return {
        "station_name": get_station_name(station),
        "station_id": get_station_id(station),
        "station_uuid": safe_get(
            station,
            [
                "station_id_uuid"
            ],
            default=""
        ),
        "station_time_zone": safe_get(
            station,
            [
                "time_zone"
            ],
            default=""
        ),
        "station_city": safe_get(
            station,
            [
                "city"
            ],
            default=""
        ),
        "station_region": safe_get(
            station,
            [
                "region"
            ],
            default=""
        ),
        "station_country": safe_get(
            station,
            [
                "country"
            ],
            default=""
        ),
        "station_latitude": safe_get(
            station,
            [
                "latitude"
            ],
            default=""
        ),
        "station_longitude": safe_get(
            station,
            [
                "longitude"
            ],
            default=""
        ),
        "station_elevation": safe_get(
            station,
            [
                "elevation"
            ],
            default=""
        )
    }


def build_row(station, sensor_block, sensor_meta, packet):
    station_metadata = build_station_metadata(station)

    station_id = station_metadata["station_id"]
    station_name = station_metadata["station_name"]

    sensor_id = get_sensor_id(sensor_block)

    device_name = get_device_name(
        sensor_meta,
        sensor_id
    )

    device_category = get_device_category(sensor_meta)

    sensor_type = safe_get(
        sensor_block,
        [
            "sensor_type"
        ],
        default=safe_get(
            sensor_meta,
            [
                "sensor_type"
            ],
            default=""
        )
    )

    data_structure_type = safe_get(
        sensor_block,
        [
            "data_structure_type"
        ],
        default=""
    )

    record_timestamp = safe_get(
        packet,
        [
            "ts"
        ],
        default=""
    )

    row = {
        "record_timestamp": record_timestamp,
        "station_name": station_name,
        "station_id": station_id,
        "station_uuid": station_metadata["station_uuid"],
        "station_time_zone": station_metadata["station_time_zone"],
        "station_city": station_metadata["station_city"],
        "station_region": station_metadata["station_region"],
        "station_country": station_metadata["station_country"],
        "station_latitude": station_metadata["station_latitude"],
        "station_longitude": station_metadata["station_longitude"],
        "station_elevation": station_metadata["station_elevation"],
        "device_name": device_name,
        "device_category": device_category,
        "sensor_id": sensor_id,
        "sensor_type": sensor_type,
        "data_structure_type": data_structure_type,
        "source": SOURCE_NAME,
        "source_record_key": f"weatherlink:{station_id}:{sensor_id}:{record_timestamp}",
        "sync_created_at": utc_now_iso(),
        "raw_json": json.dumps(
            packet,
            default=str
        )
    }

    for field_key, value in packet.items():
        if not is_scalar(value):
            continue

        row[field_key] = safe_value(value)

    return row


def import_labguru_client():
    try:
        from client.labguru_client import LabguruClient
        return LabguruClient
    except ImportError:
        from client.labguru_client import LabguruClient
        return LabguruClient


def ensure_dataset(labguru, dataset_name, desired_columns):
    existing_dataset = labguru.find_dataset_by_name(
        dataset_name
    )

    if existing_dataset:
        logger.info(
            "Found existing dataset: %s",
            dataset_name
        )

        return labguru.update_dataset_columns(
            existing_dataset,
            desired_columns
        )

    logger.info(
        "Creating dataset: %s",
        dataset_name
    )

    try:
        return labguru.create_dataset(
            dataset_name,
            desired_columns,
            parent_folder_id=LABGURU_WEATHERLINK_PARENT_FOLDER_ID
        )
    except TypeError:
        return labguru.create_dataset(
            dataset_name,
            desired_columns
        )


def sync_weatherlink_to_labguru():
    require_weatherlink_env()
    require_labguru_env()

    logger.info("Starting WeatherLink to Labguru sync.")
    logger.info("DRY_RUN=%s", DRY_RUN)
    ### Recording the latest state from sync
    state = load_state()

    last_timestamp = state[
        "last_weatherlink_timestamp"
    ]

    WeatherLinkLabguruClient = import_labguru_client()

    weatherlink = WeatherLinkClient(
        api_key=WEATHERLINK_API_KEY,
        api_secret=WEATHERLINK_API_SECRET
    )

    labguru = WeatherLinkLabguruClient(
        base_url=LABGURU_BASE_URL,
        token=LABGURU_TOKEN,
        auth_mode=LABGURU_AUTH_MODE
    )

    stations = weatherlink.get_stations()
    sensors = weatherlink.get_sensors()

    sensor_lookup = build_sensor_lookup(sensors)

    logger.info(
        "Discovered %s WeatherLink stations.",
        len(stations)
    )

    logger.info(
        "Discovered %s WeatherLink sensors.",
        len(sensors)
    )

    total_datasets = 0
    total_rows = 0

    for station in stations:
        station_id = get_station_id(station)
        station_name = get_station_name(station)

        if station_id is None:
            logger.warning(
                "Skipping station with missing station_id: %s",
                station
            )
            continue

        logger.info(
            "Pulling current conditions for station: %s [%s]",
            station_name,
            station_id
        )

        try:
            current_payload = weatherlink.get_current_conditions(
                station_id
            )
        except Exception as error:
            logger.exception(
                "Failed to pull current conditions for station %s: %s",
                station_id,
                error
            )
            continue

        sensor_blocks = extract_sensor_blocks(
            current_payload
        )

        for sensor_block in sensor_blocks:
            sensor_id = get_sensor_id(sensor_block)

            sensor_meta = sensor_lookup.get(
                sensor_id,
                {}
            )

            category = get_device_category(sensor_meta)

            if category in SKIP_CATEGORIES:
                logger.info(
                    "Skipping HEALTH sensor: station=%s sensor=%s",
                    station_name,
                    sensor_id
                )
                continue

            data_packets = extract_data_packets(
                sensor_block
            )

            if not data_packets:
                logger.info(
                    "No data packets for station=%s sensor=%s",
                    station_name,
                    sensor_id
                )
                continue

            dataset_name = build_dataset_name(
                station_name=station_name,
                sensor_meta=sensor_meta,
                sensor_id=sensor_id
            )

            desired_columns = discover_columns_from_packets(
                data_packets
            )

            try:
                dataset = ensure_dataset(
                    labguru=labguru,
                    dataset_name=dataset_name,
                    desired_columns=desired_columns
                )
            except Exception as error:
                logger.exception(
                    "Failed to create or update dataset %s: %s",
                    dataset_name,
                    error
                )
                continue

            total_datasets += 1

            for packet in data_packets:
                row = build_row(
                    station=station,
                    sensor_block=sensor_block,
                    sensor_meta=sensor_meta,
                    packet=packet
                )

                try:
                    labguru.create_vector(
                        dataset,
                        row
                    )

                    total_rows += 1

                except Exception as error:
                    logger.exception(
                        "Failed to insert row into dataset %s: %s",
                        dataset_name,
                        error
                    )

    state[
        "last_weatherlink_sync"
    ] = utc_now()

    logger.info("WeatherLink sync complete.")
    logger.info("Datasets touched: %s", total_datasets)
    logger.info("Rows inserted: %s", total_rows)




    save_state(state)

if __name__ == "__main__":
    sync_weatherlink_to_labguru()