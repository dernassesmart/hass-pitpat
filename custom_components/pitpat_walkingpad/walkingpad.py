"""PitPat WalkingPad BLE communication.

Protocol reverse-engineered from peteh/pacekeeper (C++/NimBLE).
Uses bleak_retry_connector for robust BLE connection handling,
including automatic retry, timeout handling, and ESPHome proxy support.
"""

from __future__ import annotations

import logging
import struct
import time
from collections.abc import Callable

from bleak import BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    establish_connection,
)

from .const import (
    CHARACTERISTIC_NOTIFY_UUID,
    CHARACTERISTIC_WRITE_UUID,
    BeltState,
    PitPatStatus,
)

_LOGGER = logging.getLogger(__name__)

# Command bytes (from pacekeeper TreadmillHandler.h)
CMD_STOP = 0
CMD_PAUSE = 2
CMD_START_SET_SPEED = 4

# Default user ID embedded in every packet (from pacekeeper makePacket)
_USER_ID = 58965456623


def _make_packet(command: int, speed_mhz: int) -> bytes:
    """Build a 23-byte command packet for the PitPat.

    speed_mhz: speed in units of 0.001 km/h  (e.g. 3.0 km/h = 3000)
    """
    packet = bytearray(23)
    packet[0] = 0x6A  # start byte
    packet[1] = 0x17  # length
    # bytes 2-5: reserved (0)
    packet[6] = (speed_mhz >> 8) & 0xFF
    packet[7] = speed_mhz & 0xFF
    packet[8] = 5 if speed_mhz != 0 else 1  # magic byte
    packet[9] = 0    # incline
    packet[10] = 80  # weight (default)
    packet[11] = 0   # reserved
    packet[12] = command & 0xF7  # kph mode (bit 3 = 0)
    # user ID: 8 bytes, big-endian
    uid = _USER_ID
    for i in range(8):
        packet[13 + i] = (uid >> (56 - i * 8)) & 0xFF
    # checksum: XOR of bytes 1..20
    checksum = 0
    for i in range(1, 21):
        checksum ^= packet[i]
    packet[21] = checksum
    packet[22] = 0x43  # end byte
    return bytes(packet)


def _parse_notification(data: bytes | bytearray) -> PitPatStatus | None:
    """Parse a 31+ byte BLE notification from the PitPat.

    Byte layout (from pacekeeper notifyCallback):
      [3:5]   current speed  (uint16 BE, /1000 = km/h)
      [5:7]   target speed   (uint16 BE, /1000 = km/h)
      [7:11]  distance       (uint32 BE, /1000 = km)
      [14:18] steps          (uint32 BE)
      [18:20] calories       (uint16 BE)
      [20:24] duration       (uint32 BE, /1000 = seconds)
      [26]    flags          bit3-4 = running state, bit7 = unit
    """
    if len(data) < 31:
        _LOGGER.debug("Notification too short: %d bytes — raw: %s", len(data), data.hex())
        return None

    _LOGGER.debug("Raw notification (%d bytes): %s", len(data), data.hex())

    current_speed = struct.unpack_from(">H", data, 3)[0] / 1000.0
    target_speed  = struct.unpack_from(">H", data, 5)[0] / 1000.0
    distance      = struct.unpack_from(">I", data, 7)[0] / 1000.0
    steps         = struct.unpack_from(">I", data, 14)[0]
    calories      = struct.unpack_from(">H", data, 18)[0]
    duration_sec  = struct.unpack_from(">I", data, 20)[0] // 1000

    flags = data[26]
    running_bits = flags & 0x18  # bits 3 and 4

    if running_bits == 0x18:    # 24 — countdown
        belt_state = BeltState.STARTING
    elif running_bits == 0x08:  # 8 — running
        belt_state = BeltState.ACTIVE
    elif running_bits == 0x10:  # 16 — paused
        belt_state = BeltState.STANDBY
    else:                        # 0 — stopped
        belt_state = BeltState.STOPPED

    _LOGGER.debug(
        "Parsed: state=%s speed=%.1f km/h dist=%.2f km steps=%d cal=%d dur=%ds",
        belt_state.name, current_speed, distance, steps, calories, duration_sec,
    )

    return PitPatStatus(
        belt_state=belt_state,
        speed=current_speed,
        target_speed=target_speed,
        session_distance=distance,
        session_running_time=duration_sec,
        session_steps=steps,
        session_calories=calories,
        status_timestamp=time.monotonic(),
    )


class WalkingPad:
    """Represents a PitPat WalkingPad device over BLE."""

    def __init__(self, name: str, ble_device: BLEDevice) -> None:
        self._name = name
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._connected = False
        self._callbacks: list[Callable[[PitPatStatus], None]] = []

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def mac(self) -> str:
        return self._ble_device.address

    @property
    def name(self) -> str:
        return self._name

    @property
    def connected(self) -> bool:
        client = self._client  # local ref avoids race with disconnect()
        return self._connected and client is not None and client.is_connected

    def register_status_callback(self, callback: Callable[[PitPatStatus], None]) -> None:
        self._callbacks.append(callback)

    def update_ble_device(self, ble_device: BLEDevice) -> None:
        """Refresh the BLEDevice handle (call before reconnecting)."""
        self._ble_device = ble_device

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the device and subscribe to notifications."""
        if self.connected:
            return

        _LOGGER.debug(
            "Connecting to PitPat WalkingPad %s (rssi=%s)",
            self.mac,
            getattr(self._ble_device, "rssi", "?"),
        )
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self._name,
                disconnected_callback=self._on_disconnect,
            )
            _LOGGER.debug("BLE connection established, subscribing to notifications")
            await self._client.start_notify(
                CHARACTERISTIC_NOTIFY_UUID, self._on_notification
            )
            self._connected = True
            _LOGGER.info(
                "Connected to PitPat WalkingPad %s and subscribed to notifications",
                self.mac,
            )
        except BLEAK_RETRY_EXCEPTIONS as err:
            _LOGGER.warning(
                "Cannot connect to PitPat WalkingPad %s: %s — will retry next poll",
                self.mac, err,
            )
            self._connected = False
            self._client = None
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Unexpected error connecting to PitPat WalkingPad %s: %s",
                self.mac, err,
            )
            self._connected = False
            self._client = None

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        _LOGGER.debug("Disconnecting from PitPat WalkingPad %s", self.mac)
        self._connected = False
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:  # pylint: disable=broad-except
                pass
            self._client = None

    def _on_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.warning(
            "PitPat WalkingPad %s disconnected unexpectedly", self.mac
        )
        self._connected = False

    # ------------------------------------------------------------------
    # Notification handler
    # ------------------------------------------------------------------

    def _on_notification(self, _sender: int, data: bytearray) -> None:
        status = _parse_notification(data)
        if status is not None:
            for callback in self._callbacks:
                callback(status)

    # ------------------------------------------------------------------
    # State polling (called by coordinator every 5 s)
    # ------------------------------------------------------------------

    async def update_state(self) -> None:
        """Ensure we are connected; notifications arrive automatically."""
        if not self.connected:
            _LOGGER.debug("Not connected — attempting to connect")
            await self.connect()
        else:
            _LOGGER.debug("Connection alive, waiting for next notification")

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def _send(self, command: int, speed_mhz: int = 0) -> None:
        if not self.connected:
            _LOGGER.debug("Not connected for command %d — connecting first", command)
            await self.connect()
        if not self.connected:
            _LOGGER.warning("Cannot send command %d: still not connected", command)
            return
        try:
            packet = _make_packet(command, speed_mhz)
            _LOGGER.debug("Sending command %d speed_mhz=%d: %s", command, speed_mhz, packet.hex())
            await self._client.write_gatt_char(  # type: ignore[union-attr]
                CHARACTERISTIC_WRITE_UUID, packet, response=True
            )
            _LOGGER.debug("Command %d sent successfully", command)
        except BleakError as err:
            _LOGGER.warning("BLE write error (command %d): %s", command, err)
            self._connected = False

    async def start_belt(self) -> None:
        """Start the belt (speed 0 = let device decide)."""
        _LOGGER.debug("start_belt()")
        await self._send(CMD_START_SET_SPEED, 0)

    async def stop_belt(self) -> None:
        """Stop the belt."""
        _LOGGER.debug("stop_belt()")
        await self._send(CMD_STOP, 0)

    async def pause_belt(self) -> None:
        """Pause the belt."""
        _LOGGER.debug("pause_belt()")
        await self._send(CMD_PAUSE, 0)

    async def set_speed(self, speed_kmh: float) -> None:
        """Set belt speed in km/h (0.5 – 6.0)."""
        speed_mhz = int(round(speed_kmh * 1000))
        _LOGGER.debug("set_speed(%.1f km/h = %d mhz)", speed_kmh, speed_mhz)
        await self._send(CMD_START_SET_SPEED, speed_mhz)
