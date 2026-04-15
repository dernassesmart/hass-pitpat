"""PitPat WalkingPad speed control entity."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PitPatIntegrationData
from .const import DOMAIN, BeltState
from .coordinator import PitPatCoordinator

NUMBER_KEY = "pitpat_speed"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entry_data: PitPatIntegrationData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PitPatSpeedNumber(entry_data["coordinator"])])


class PitPatSpeedNumber(CoordinatorEntity[PitPatCoordinator], NumberEntity):
    """Adjust the belt speed while it is running."""

    _attr_has_entity_name = True
    _attr_name = "Speed"
    _attr_icon = "mdi:speedometer"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_min_value = 0.5
    _attr_native_max_value = 6.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: PitPatCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.mac}-{NUMBER_KEY}"

    @property
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

    @property
    def native_value(self) -> float:
        return self.coordinator.data.get("target_speed", 0.0)

    @property
    def available(self) -> bool:
        return self.coordinator.connected

    async def async_set_native_value(self, value: float) -> None:
        belt_state = self.coordinator.data.get("belt_state", BeltState.STOPPED)
        if belt_state not in (BeltState.ACTIVE, BeltState.STARTING):
            return
        await self.coordinator.device.set_speed(value)
