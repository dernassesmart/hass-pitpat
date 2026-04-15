"""Data coordinator for the PitPat WalkingPad integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, BeltState, PitPatStatus
from .walkingpad import WalkingPad

_LOGGER = logging.getLogger(__name__)

STATUS_UPDATE_INTERVAL = timedelta(seconds=5)
STATUS_UPDATE_TIMEOUT_SECONDS = 15


class PitPatCoordinator(DataUpdateCoordinator[PitPatStatus]):
    """Coordinator that polls the PitPat and distributes updates."""

    def __init__(self, hass: HomeAssistant, device: WalkingPad) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            always_update=False,
            update_interval=STATUS_UPDATE_INTERVAL,
            update_method=None,
        )
        self.device = device
        self.device.register_status_callback(self._async_handle_update)
        self.data: PitPatStatus = PitPatStatus(
            belt_state=BeltState.STOPPED,
            speed=0.0,
            target_speed=0.0,
            session_distance=0.0,
            session_running_time=0,
            session_steps=0,
            session_calories=0,
            status_timestamp=0.0,
        )

    # ------------------------------------------------------------------
    # DataUpdateCoordinator overrides
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> PitPatStatus:
        async with asyncio.timeout(STATUS_UPDATE_TIMEOUT_SECONDS):
            await self.device.update_state()
        # Actual data arrives via the notification callback below.
        return self.data

    @property
    def connected(self) -> bool:
        return self.device.connected

    # ------------------------------------------------------------------
    # Notification callback (called from walkingpad.py)
    # ------------------------------------------------------------------

    @callback
    def _async_handle_update(self, status: PitPatStatus) -> None:
        if status["status_timestamp"] > self.data["status_timestamp"]:
            _LOGGER.debug("PitPat status update: %s", status)
            self.async_set_updated_data(status)

    # ------------------------------------------------------------------
    # Listener lifecycle: connect on first listener, disconnect on last
    # ------------------------------------------------------------------

    @callback
    def async_add_listener(
        self, update_callback: CALLBACK_TYPE, context: Any = None
    ) -> Callable[[], None]:
        if not self._listeners:
            async_call_later(
                self.hass,
                0,
                HassJob(self._async_connect, "Connect to PitPat WalkingPad"),
            )
        return super().async_add_listener(update_callback, context)

    @callback
    def _unschedule_refresh(self) -> None:
        async_call_later(
            self.hass,
            0,
            HassJob(self._async_disconnect, "Disconnect PitPat WalkingPad"),
        )
        return super()._unschedule_refresh()

    async def _async_connect(self, *_: Any) -> None:
        await self.device.connect()

    async def _async_disconnect(self, *_: Any) -> None:
        await self.device.disconnect()
