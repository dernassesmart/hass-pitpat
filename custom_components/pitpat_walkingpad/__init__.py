"""PitPat WalkingPad Home Assistant integration."""

from __future__ import annotations

import logging
from typing import TypedDict

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_MAC, CONF_NAME, DOMAIN
from .coordinator import PitPatCoordinator
from .walkingpad import WalkingPad

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


class PitPatIntegrationData(TypedDict):
    device: WalkingPad
    coordinator: PitPatCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PitPat WalkingPad from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    address = entry.data[CONF_MAC]
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address, connectable=True
    )
    if ble_device is None:
        count_scanners = bluetooth.async_scanner_count(hass, connectable=True)
        if count_scanners < 1:
            raise ConfigEntryNotReady(
                "No Bluetooth scanner found. Enable the Bluetooth integration "
                "or add an ESPHome Bluetooth proxy."
            )
        raise ConfigEntryNotReady(
            f"PitPat WalkingPad with address {address} not found. "
            "Make sure the device is powered on and in range."
        )

    name = entry.data.get(CONF_NAME) or DOMAIN
    device = WalkingPad(name, ble_device)
    coordinator = PitPatCoordinator(hass, device)

    hass.data[DOMAIN][entry.entry_id] = PitPatIntegrationData(
        device=device, coordinator=coordinator
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
