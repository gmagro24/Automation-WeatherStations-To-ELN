# client/labguru_config.py

import os

DRY_RUN = os.getenv(
    "DRY_RUN",
    "true"
).lower() == "true"

AUTO_ADD_COLUMNS = os.getenv(
    "AUTO_ADD_COLUMNS",
    "true"
).lower() == "true"

LABGURU_DATASETS_PATH = "/api/v1/datasets"

LABGURU_DATASET_DETAIL_PATH_TEMPLATE = (
    "/api/v1/datasets/{dataset_id}"
)

LABGURU_VECTOR_CREATE_PATH_TEMPLATE = (
    "/api/v1/datasets/{dataset_id}/vectors"
)