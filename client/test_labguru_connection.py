"""
Read-only Labguru connectivity test.

This script only performs a GET request to the datasets endpoint.
It does not create datasets or upload vectors.
"""

import os
import sys
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    env_file = PROJECT_ROOT / ".env"

    if env_file.exists():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value

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


def normalize_path(path):
    if not path:
        return ""

    return path if path.startswith("/") else f"/{path}"


def infer_datasets_path(base_url, configured_path):
    if configured_path:
        return normalize_path(configured_path)

    parsed = urlparse(base_url)
    base_path = parsed.path.rstrip("/")

    # If base already includes /api/v1, avoid duplicating it.
    if base_path.endswith("/api/v1"):
        return "/datasets"

    return "/api/v1/datasets"


def build_auth(auth_mode, token):
    mode = (auth_mode or "bearer").strip().lower()

    headers = {
        "Accept": "application/json",
    }

    params = {}

    if mode == "bearer":
        headers["Authorization"] = f"Bearer {token}"
    elif mode == "query":
        params["token"] = token
    else:
        raise RuntimeError(
            f"Unsupported LABGURU_AUTH_MODE: {auth_mode}. Use 'bearer' or 'query'."
        )

    return headers, params


@dataclass
class ProbeResult:
    base_url: str
    path: str
    auth_mode: str
    status_code: int
    content_type: str


def fetch_datasets(base_url, datasets_path, auth_mode, token):
    headers, params = build_auth(auth_mode, token)
    url = f"{base_url.rstrip('/')}{datasets_path}"

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=60,
    )

    return response


def probe_variants(base_url, token):
    candidates = [
        (base_url.rstrip("/"), "/api/v1/datasets"),
        (base_url.rstrip("/"), "/api/v1/datasets.json"),
    ]

    parsed = urlparse(base_url)
    if parsed.path.rstrip("/") == "/api/v1":
        origin = f"{parsed.scheme}://{parsed.netloc}"
        candidates.extend(
            [
                (origin, "/api/v1/datasets"),
                (origin, "/api/v1/datasets.json"),
            ]
        )

    results = []

    seen = set()
    for candidate_base, path in candidates:
        for mode in ["bearer", "query"]:
            key = (candidate_base, path, mode)
            if key in seen:
                continue

            seen.add(key)

            try:
                response = fetch_datasets(
                    base_url=candidate_base,
                    datasets_path=path,
                    auth_mode=mode,
                    token=token,
                )
                content_type = response.headers.get("Content-Type", "")
                results.append(
                    ProbeResult(
                        base_url=candidate_base,
                        path=path,
                        auth_mode=mode,
                        status_code=response.status_code,
                        content_type=content_type,
                    )
                )
            except Exception:
                results.append(
                    ProbeResult(
                        base_url=candidate_base,
                        path=path,
                        auth_mode=mode,
                        status_code=-1,
                        content_type="request_error",
                    )
                )

    return results


def main():
    base_url = get_setting("LABGURU_BASE_URL", "").rstrip("/")
    token = get_setting("LABGURU_TOKEN", "")
    auth_mode = get_setting("LABGURU_AUTH_MODE", "bearer")
    configured_path = get_setting("LABGURU_DATASETS_PATH", "")

    if not base_url:
        raise RuntimeError("Missing LABGURU_BASE_URL")

    if not token:
        raise RuntimeError("Missing LABGURU_TOKEN")

    datasets_path = infer_datasets_path(base_url, configured_path)
    url = f"{base_url}{datasets_path}"

    headers, params = build_auth(auth_mode, token)

    print("Testing Labguru connection (read-only)...")
    print("Base URL:", base_url)
    print("Datasets path:", datasets_path)
    print("Auth mode:", auth_mode)

    response = requests.get(url, headers=headers, params=params, timeout=60)

    print("HTTP status:", response.status_code)

    if response.status_code == 406:
        print("Received HTTP 406 (Not Acceptable).")
        print("This usually indicates Labguru is rejecting this host/path for API access.")
        print("Trying common read-only API variants...")

        probe_results = probe_variants(base_url, token)
        for item in probe_results:
            print(
                f"- base={item.base_url} path={item.path} auth={item.auth_mode} "
                f"status={item.status_code} content_type={item.content_type}"
            )

        print("Suggested next checks:")
        print("1) Confirm your exact Labguru API base URL from Labguru settings/docs.")
        print("2) Confirm whether your token expects bearer or query auth mode.")
        print("3) Ensure API access is enabled for your account/workspace.")

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        print("Connection test failed.")
        print(f"Reason: {error}")

        request_id = response.headers.get("x-request-id", "")
        if request_id:
            print("Labguru request id:", request_id)

        print("No data was pushed. This test is read-only.")
        sys.exit(1)

    data = response.json()

    if isinstance(data, list):
        datasets = data
    elif isinstance(data, dict):
        datasets = []
        for key in ["datasets", "data", "results", "items"]:
            if isinstance(data.get(key), list):
                datasets = data[key]
                break
    else:
        datasets = []

    print("Connection OK")
    print("Datasets returned:", len(datasets))

    preview = datasets[:3] if isinstance(datasets, list) else []
    print("Preview:")
    print(json.dumps(preview, indent=2, default=str))


if __name__ == "__main__":
    main()
