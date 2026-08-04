"""
Labguru API Client

Provides a centralized interface for interacting with Labguru datasets
and vectors. Handles dataset discovery, creation, schema updates,
row insertion, authentication, and dry-run testing.

Used by:
    - weatherlink_to_labguru.py
    - licor_to_labguru.py

Supports:
    - Dataset lookup
    - Dataset creation
    - Automatic column management
    - Vector (row) insertion
    - Parent folder assignment
    - Dry-run validation
"""

import json

import requests

from weatherLink.weatherlink_to_labguru import DRY_RUN, logger, LABGURU_DATASETS_PATH, safe_get, \
    LABGURU_DATASET_DETAIL_PATH_TEMPLATE, build_base_columns, AUTO_ADD_COLUMNS, LABGURU_VECTOR_CREATE_PATH_TEMPLATE

# ======================== Labguru Client ====================================

class LabguruClient:
    def __init__(self, base_url, token, auth_mode="bearer"):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.auth_mode = auth_mode
        self.session = requests.Session()

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def _params(self):
        if self.auth_mode == "query":
            return {
                "token": self.token
            }

        return {}

    def get_datasets(self):
        if DRY_RUN:
            logger.info("[DRY RUN] Skipping Labguru dataset lookup.")
            return []

        url = self._url(LABGURU_DATASETS_PATH)

        response = self.session.get(
            url,
            headers=self._headers(),
            params=self._params(),
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ["datasets", "data", "results", "items"]:
                if isinstance(data.get(key), list):
                    return data[key]

        return []

    def get_dataset_id(self, dataset):
        return safe_get(
            dataset,
            ["id", "dataset_id"],
            default=None
        )

    def get_dataset_name(self, dataset):
        return str(
            safe_get(dataset, ["name", "title"], default="")
        )

    def find_dataset_by_name(self, dataset_name):
        datasets = self.get_datasets()

        for dataset in datasets:
            if self.get_dataset_name(dataset) == dataset_name:
                return dataset

        return None

    def create_dataset(
            self,
            dataset_name,
            columns,
            parent_folder_id=None
    ):
        logger.info(
            "Creating Labguru dataset: %s",
            dataset_name
        )

        payload = {
            "name": dataset_name,
            "title": dataset_name,
            "columns": columns,
            "fields": columns,
            "headers": columns,
        }

        if parent_folder_id:
            payload["parent_folder_id"] = parent_folder_id

        if DRY_RUN:
            logger.info(
                "[DRY RUN] Would create dataset:"
            )

            logger.info(
                json.dumps(
                    payload,
                    indent=2
                )
            )

            return {
                "id": f"dry-run-{dataset_name}",
                "name": dataset_name,
                "columns": columns,
            }

        url = self._url(
            LABGURU_DATASETS_PATH
        )

        response = self.session.post(
            url,
            headers=self._headers(),
            params=self._params(),
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        return response.json()

    def get_dataset_detail(self, dataset_id):
        if DRY_RUN:
            return {}

        path = LABGURU_DATASET_DETAIL_PATH_TEMPLATE.format(dataset_id=dataset_id)
        url = self._url(path)

        response = self.session.get(
            url,
            headers=self._headers(),
            params=self._params(),
            timeout=60
        )

        response.raise_for_status()
        return response.json()

    def extract_columns_from_dataset(self, dataset):
        for key in ["columns", "fields", "headers"]:
            candidate = dataset.get(key)

            if isinstance(candidate, list):
                columns = []

                for item in candidate:
                    if isinstance(item, str):
                        columns.append(item)
                    elif isinstance(item, dict):
                        name = safe_get(item, ["name", "title", "label"], default="")
                        if name:
                            columns.append(str(name))

                if columns:
                    return columns

        dataset_id = self.get_dataset_id(dataset)

        if dataset_id:
            detail = self.get_dataset_detail(dataset_id)

            for key in ["columns", "fields", "headers"]:
                candidate = detail.get(key)

                if isinstance(candidate, list):
                    columns = []

                    for item in candidate:
                        if isinstance(item, str):
                            columns.append(item)
                        elif isinstance(item, dict):
                            name = safe_get(item, ["name", "title", "label"], default="")
                            if name:
                                columns.append(str(name))

                    if columns:
                        return columns

        return []

    def update_dataset_columns(self, dataset, desired_columns):
        existing_columns = self.extract_columns_from_dataset(dataset)

        if not existing_columns:
            existing_columns = build_base_columns()

        missing_columns = [
            column for column in desired_columns
            if column not in existing_columns
        ]

        if not missing_columns:
            return dataset

        logger.info("Missing Labguru columns: %s", missing_columns)

        if not AUTO_ADD_COLUMNS:
            logger.warning("AUTO_ADD_COLUMNS=false, so missing columns were not added.")
            return dataset

        final_columns = existing_columns + missing_columns

        payload = {
            "columns": final_columns,
            "fields": final_columns,
            "headers": final_columns,
        }

        if DRY_RUN:
            logger.info("[DRY RUN] Would update dataset columns:")
            logger.info(json.dumps(payload, indent=2))
            dataset["columns"] = final_columns
            return dataset

        dataset_id = self.get_dataset_id(dataset)

        if not dataset_id:
            raise RuntimeError(f"Cannot update columns because dataset has no ID: {dataset}")

        path = LABGURU_DATASET_DETAIL_PATH_TEMPLATE.format(dataset_id=dataset_id)
        url = self._url(path)

        response = self.session.patch(
            url,
            headers=self._headers(),
            params=self._params(),
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        return response.json()

    def create_vector(self, dataset, row):
        dataset_id = self.get_dataset_id(dataset)

        if not dataset_id:
            raise RuntimeError(f"Cannot insert row because dataset has no ID: {dataset}")

        payload = {
            "data": row,
            "vector": {
                "data": row
            }
        }

        if DRY_RUN:
            logger.info("[DRY RUN] Would insert Labguru row:")
            logger.info(json.dumps(payload, indent=2, default=str))
            return {
                "status": "dry-run",
                "dataset_id": dataset_id,
                "row": row,
            }

        path = LABGURU_VECTOR_CREATE_PATH_TEMPLATE.format(dataset_id=dataset_id)
        url = self._url(path)

        response = self.session.post(
            url,
            headers=self._headers(),
            params=self._params(),
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        return response.json()
