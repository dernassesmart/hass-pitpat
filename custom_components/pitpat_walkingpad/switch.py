"""PitPat WalkingPad belt switch entity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PitPatIntegrationData
from .const import DOMAIN, BeltState
from .coordinator import PitPatCoordinator, STATUS_UPDATE_INTERVAL
from .utils import TemporaryValue

SWITCH_KEY = "pitpat_belt_switch"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entry_data: PitPatIntegrationData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PitPatBeltSwitch(entry_data["coordinator"])])


class PitPatBeltSwitch(CoordinatorEntity[PitPatCoordinator], SwitchEntity):
    """Start / stop the PitPat belt."""

    _attr_has_entity_name = True
    _attr_name = "Belt"
    _attr_icon = "mdi:cog-play"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: PitPatCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.mac}-{SWITCH_KEY}"
        self._temporary_state: TemporaryValue[BeltState] = TemporaryValue()

    @property
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        current_ts = self.coordinator.data.get("status_timestamp", 0)
        current_state = self.coordinator.data.get("belt_state", BeltState.STOPPED)

        # Drop optimistic state once device confirms (unless still in countdown)
        if (
            self._temporary_state.has_value
            and current_state != BeltState.STARTING
            and self._temporary_state.is_expired(current_ts)
        ):
            self._temporary_state.reset()

        belt_state = self._temporary_state.peek(current_state)
        return belt_state in (BeltState.ACTIVE, BeltState.STARTING)

    @property
    def available(self) -> bool:
        return self.coordinator.connected

    def _set_temporary(self, state: BeltState) -> None:
        expiry = (
            self.coordinator.data.get("status_timestamp", 0)
            + STATUS_UPDATE_INTERVAL.total_seconds()
        )
        self._temporary_state.set(state, expiry)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._set_temporary(BeltState.STARTING)
        await self.coordinator.device.start_belt()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._set_temporary(BeltState.STOPPED)
        await self.coordinator.device.stop_belt()
