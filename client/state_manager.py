"""
Synchronization State Manager

Provides persistent state tracking for WeatherLink and LI-COR
synchronization jobs. Handles reading and writing sync metadata,
timestamps, and future duplicate-prevention checkpoints.

State File:
    state/sync_state.json
"""
import json
from pathlib import Path
from datetime import datetime, timezone

STATE_FILE = (
    Path(__file__).resolve().parents[1]
    / "state"
    / "sync_state.json"
)

DEFAULT_STATE = {
    "last_weatherlink_timestamp": None,
    "last_licor_timestamp": None,
    "last_weatherlink_sync": None,
    "last_licor_sync": None,
}


def load_state():

    if not STATE_FILE.exists():

        STATE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        save_state(DEFAULT_STATE)

        return DEFAULT_STATE.copy()

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_state(state):

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            indent=2
        )


def utc_now():

    return (
        datetime.now(timezone.utc)
        .isoformat()
    )