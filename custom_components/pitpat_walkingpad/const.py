"""Constants for the PitPat WalkingPad integration."""

from enum import IntEnum, unique
from typing import Final, TypedDict

DOMAIN: Final = "pitpat_walkingpad"

CONF_MAC: Final = "mac"
CONF_NAME: Final = "name"

# BLE UUIDs (from pacekeeper/platform.h)
SERVICE_UUID: Final = "0000fba0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_WRITE_UUID: Final = "0000fba1-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_NOTIFY_UUID: Final = "0000fba2-0000-1000-8000-00805f9b34fb"


@unique
class BeltState(IntEnum):
    """Possible belt states."""

    STOPPED = 0
    ACTIVE = 1
    STANDBY = 5   # paused
    STARTING = 9  # countdown
    UNKNOWN = 1000


class PitPatStatus(TypedDict):
    """State of the PitPat at a specific point in time."""

    belt_state: BeltState
    speed: float          # current speed in km/h
    target_speed: float   # target speed in km/h
    session_distance: float   # km
    session_running_time: int  # seconds
    session_steps: int
    session_calories: int
    status_timestamp: float   # monotonic time
