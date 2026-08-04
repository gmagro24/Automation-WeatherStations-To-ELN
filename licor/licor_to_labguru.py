"""
LI-COR → Labguru Synchronization

Automatically discovers LI-COR stations and sensors,
creates or updates Labguru datasets, uploads current sensor
data, and records synchronization state.

State Tracking:
    state/sync_state.json

Author: Gina Magro
"""
import os
import sys
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from client.state_manager import load_state, utc_now, save_state

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


from client.labguru_client import LabguruClient


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


LICOR_API_BASE_URL = get_setting(
    "LICOR_API_BASE_URL",
    "https://api.licor.cloud"
).rstrip("/")

LICOR_API_TOKEN = get_setting(
    "LICOR_API_TOKEN",
    ""
)

LICOR_LOOKBACK_DAYS = int(
    get_setting(
        "LICOR_LOOKBACK_DAYS",
        "30"
    )
)

LABGURU_BASE_URL = get_setting(
    "LABGURU_BASE_URL",
    ""
).rstrip("/")

LABGURU_TOKEN = get_setting(
    "LABGURU_TOKEN",
    ""
)

LABGURU_AUTH_MODE = get_setting(
    "LABGURU_AUTH_MODE",
    "bearer"
).lower()

LABGURU_LICOR_PARENT_FOLDER_ID = get_setting(
    "LABGURU_LICOR_PARENT_FOLDER_ID",
    ""
)

DRY_RUN = str(
    get_setting(
        "DRY_RUN",
        "true"
    )
).lower() == "true"

SOURCE_NAME = "LI-COR"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def format_licor_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


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

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def clean_dataset_name(value):
    text = str(value or "").strip()
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    text = " ".join(text.split())
    return text[:180]


def require_env():
    missing = []

    if not LICOR_API_TOKEN:
        missing.append("LICOR_API_TOKEN")

    if not LABGURU_BASE_URL and not DRY_RUN:
        missing.append("LABGURU_BASE_URL")

    if not LABGURU_TOKEN and not DRY_RUN:
        missing.append("LABGURU_TOKEN")

    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
        )


class LicorClient:
    def __init__(self, base_url=None, token=None):
        self.base_url = (base_url or LICOR_API_BASE_URL).rstrip("/")
        self.token = token or LICOR_API_TOKEN
        self.session = requests.Session()

    def headers(self):
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def get(self, path, params=None):
        if params is None:
            params = {}

        url = f"{self.base_url}{path}"

        response = self.session.get(
            url,
            headers=self.headers(),
            params=params,
            timeout=60
        )

        if response.status_code >= 400:
            logger.error("LI-COR API request failed")
            logger.error("URL: %s", url)
            logger.error("Status: %s", response.status_code)
            logger.error(response.text)

        response.raise_for_status()
        return response.json()

    def get_devices(self):
        return self.get("/v2/devices")

    def get_newa_data(
        self,
        device_serial_number,
        start_date_time,
        end_date_time
    ):
        params = {
            "start_date_time": start_date_time,
            "end_date_time": end_date_time
        }

        path = f"/v1/newa/{device_serial_number}"

        return self.get(
            path,
            params=params
        )


def extract_devices(devices_response):
    if isinstance(devices_response, dict):
        devices = devices_response.get("devices", [])

        if isinstance(devices, list):
            return devices

    if isinstance(devices_response, list):
        return devices_response

    return []


def extract_records(data_response):
    if isinstance(data_response, list):
        return data_response

    if isinstance(data_response, dict):
        for key in [
            "data",
            "records",
            "measurements",
            "results",
            "items"
        ]:
            value = data_response.get(key)

            if isinstance(value, list):
                return value

        if data_response.get("message") and not data_response.get("data"):
            return []

        return [data_response]

    return []


def build_dataset_name(device):
    device_name = safe_get(
        device,
        ["deviceName"],
        default="Unknown LI-COR Device"
    )

    device_serial = safe_get(
        device,
        ["deviceSerialNumber"],
        default="unknown"
    )

    return clean_dataset_name(
        f"{device_name} - LI-COR"
    )


def build_base_columns():
    return [
        "record_timestamp",
        "source",
        "device_name",
        "device_serial_number",
        "product_code",
        "unit_system",
        "last_connection_time",
        "logging_state",
        "alarmed",
        "source_record_key",
        "sync_created_at",
        "raw_json"
    ]


def add_latest_sensor_columns(columns, device):
    sensors = device.get("sensors", [])

    if not isinstance(sensors, list):
        return columns

    for sensor in sensors:
        measurement_type = safe_get(
            sensor,
            ["measurementType"],
            default=""
        )

        units = safe_get(
            sensor,
            ["units"],
            default=""
        )

        if not measurement_type:
            continue

        if units:
            column_name = f"{measurement_type} ({units})"
        else:
            column_name = measurement_type

        sensor_col = f"{measurement_type} Sensor Serial Number"

        if column_name not in columns:
            columns.append(column_name)

        if sensor_col not in columns:
            columns.append(sensor_col)

    return columns


def discover_columns_from_records(records, device):
    columns = build_base_columns()
    columns = add_latest_sensor_columns(columns, device)

    for record in records:
        if not isinstance(record, dict):
            continue

        for key, value in record.items():
            if is_scalar(value) and key not in columns:
                columns.append(key)

    return columns


def build_latest_row(device):
    device_name = safe_get(
        device,
        ["deviceName"],
        default=""
    )

    device_serial = safe_get(
        device,
        ["deviceSerialNumber"],
        default=""
    )

    product_code = safe_get(
        device,
        ["productCode"],
        default=""
    )

    unit_system = safe_get(
        device,
        ["unitSystem"],
        default=""
    )

    last_connection_time = safe_get(
        device,
        ["lastConnectionTime"],
        default=""
    )

    logging_state = safe_get(
        device,
        ["loggingState"],
        default=""
    )

    alarmed = safe_get(
        device,
        ["alarmed"],
        default=""
    )

    row = {
        "record_timestamp": last_connection_time,
        "source": SOURCE_NAME,
        "device_name": device_name,
        "device_serial_number": device_serial,
        "product_code": product_code,
        "unit_system": unit_system,
        "last_connection_time": last_connection_time,
        "logging_state": logging_state,
        "alarmed": alarmed,
        "source_record_key": f"licor:{device_serial}:{last_connection_time}",
        "sync_created_at": utc_now_iso(),
        "raw_json": json.dumps(
            device,
            default=str
        )
    }

    sensors = device.get("sensors", [])

    if not isinstance(sensors, list):
        return row

    for sensor in sensors:
        measurement_type = safe_get(
            sensor,
            ["measurementType"],
            default=""
        )

        units = safe_get(
            sensor,
            ["units"],
            default=""
        )

        latest = safe_get(
            sensor,
            ["latest"],
            default=None
        )

        sensor_serial = safe_get(
            sensor,
            ["sensorSerialNumber"],
            default=""
        )

        if not measurement_type:
            continue

        if units:
            column_name = f"{measurement_type} ({units})"
        else:
            column_name = measurement_type

        row[column_name] = latest
        row[f"{measurement_type} Sensor Serial Number"] = sensor_serial

    return row


def build_row_from_record(device, record):
    latest_row = build_latest_row(device)

    record_timestamp = safe_get(
        record,
        [
            "timestamp",
            "time",
            "dateTime",
            "datetime",
            "recordedAt",
            "createdAt"
        ],
        default=latest_row.get("record_timestamp", "")
    )

    row = dict(latest_row)

    row["record_timestamp"] = record_timestamp
    row["source_record_key"] = (
        f"licor:{row['device_serial_number']}:{record_timestamp}"
    )

    row["raw_json"] = json.dumps(
        record,
        default=str
    )

    for key, value in record.items():
        if is_scalar(value):
            row[key] = safe_value(value)

    return row


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
            parent_folder_id=LABGURU_LICOR_PARENT_FOLDER_ID
        )
    except TypeError:
        return labguru.create_dataset(
            dataset_name,
            desired_columns
        )


def sync_licor_to_labguru():
    require_env()

    logger.info("Starting LI-COR API to Labguru sync.")
    logger.info("DRY_RUN=%s", DRY_RUN)

    state = load_state()

    last_licor_timestamp = state.get(
        "last_licor_timestamp"
    )

    licor = LicorClient()

    labguru = LabguruClient(
        base_url=LABGURU_BASE_URL,
        token=LABGURU_TOKEN,
        auth_mode=LABGURU_AUTH_MODE
    )

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=LICOR_LOOKBACK_DAYS)

    start_date_time = format_licor_datetime(start_dt)
    end_date_time = format_licor_datetime(end_dt)

    logger.info(
        "LI-COR query window: %s to %s",
        start_date_time,
        end_date_time
    )

    devices_response = licor.get_devices()
    devices = extract_devices(devices_response)

    logger.info(
        "Discovered %s LI-COR devices.",
        len(devices)
    )

    total_datasets = 0
    total_rows = 0

    for device in devices:
        device_name = safe_get(
            device,
            ["deviceName"],
            default="Unknown LI-COR Device"
        )

        device_serial = safe_get(
            device,
            ["deviceSerialNumber"],
            default=""
        )

        if not device_serial:
            logger.warning(
                "Skipping device with missing serial number: %s",
                device
            )
            continue

        logger.info(
            "Processing device: %s [%s]",
            device_name,
            device_serial
        )

        try:
            data_response = licor.get_newa_data(
                device_serial_number=device_serial,
                start_date_time=start_date_time,
                end_date_time=end_date_time
            )

            records = extract_records(data_response)

        except Exception as error:
            logger.warning(
                "Could not retrieve LI-COR historical data for %s. Using latest values. Error: %s",
                device_serial,
                error
            )

            records = []

        dataset_name = build_dataset_name(device)

        if records:
            desired_columns = discover_columns_from_records(
                records,
                device
            )
        else:
            latest_row = build_latest_row(device)
            desired_columns = list(latest_row.keys())

        dataset = ensure_dataset(
            labguru=labguru,
            dataset_name=dataset_name,
            desired_columns=desired_columns
        )

        total_datasets += 1

        if records:
            for record in records:
                if not isinstance(record, dict):
                    continue

                row = build_row_from_record(
                    device,
                    record
                )

                labguru.create_vector(
                    dataset,
                    row
                )

                total_rows += 1

        else:
            row = build_latest_row(device)

            labguru.create_vector(
                dataset,
                row
            )

            total_rows += 1

    state["last_licor_sync"] = utc_now()
    save_state(state)

    logger.info("LI-COR API sync complete.")
    logger.info("Datasets touched: %s", total_datasets)
    logger.info("Rows inserted: %s", total_rows)



if __name__ == "__main__":
    sync_licor_to_labguru()