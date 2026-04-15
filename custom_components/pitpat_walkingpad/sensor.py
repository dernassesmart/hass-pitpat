"""PitPat WalkingPad sensor entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfSpeed, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PitPatIntegrationData
from .const import DOMAIN, BeltState, PitPatStatus
from .coordinator import PitPatCoordinator


@dataclass(kw_only=True)
class PitPatSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PitPatStatus], StateType]


SENSORS: tuple[PitPatSensorDescription, ...] = (
    PitPatSensorDescription(
        device_class=SensorDeviceClass.SPEED,
        icon="mdi:speedometer",
        key="pitpat_current_speed",
        name="Current Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda s: s.get("speed", 0.0),
    ),
    PitPatSensorDescription(
        device_class=SensorDeviceClass.SPEED,
        icon="mdi:speedometer-medium",
        key="pitpat_target_speed",
        name="Target Speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda s: s.get("target_speed", 0.0),
    ),
    PitPatSensorDescription(
        device_class=SensorDeviceClass.DISTANCE,
        icon="mdi:walk",
        key="pitpat_distance",
        name="Distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda s: s.get("session_distance", 0.0),
    ),
    PitPatSensorDescription(
        icon="mdi:shoe-print",
        key="pitpat_steps",
        name="Steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda s: s.get("session_steps", 0),
    ),
    PitPatSensorDescription(
        icon="mdi:fire",
        key="pitpat_calories",
        name="Calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda s: s.get("session_calories", 0),
    ),
    PitPatSensorDescription(
        icon="mdi:timer",
        key="pitpat_duration_minutes",
        name="Duration",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda s: round(s.get("session_running_time", 0) / 60, 1),
    ),
    PitPatSensorDescription(
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:state-machine",
        key="pitpat_state",
        name="State",
        options=[e.name.lower() for e in BeltState],
        value_fn=lambda s: s.get("belt_state", BeltState.UNKNOWN).name.lower(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    entry_data: PitPatIntegrationData = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    async_add_entities(
        PitPatSensor(coordinator, desc) for desc in SENSORS
    )


class PitPatSensor(CoordinatorEntity[PitPatCoordinator], SensorEntity):
    """A sensor entity for the PitPat WalkingPad."""

    entity_description: PitPatSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PitPatCoordinator, description: PitPatSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.mac}-{description.key}"

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        return self.coordinator.connected
