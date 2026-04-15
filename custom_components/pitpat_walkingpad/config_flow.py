"""Config flow for PitPat WalkingPad integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import CONF_MAC, CONF_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC): str,
        vol.Required(CONF_NAME, default="PitPat WalkingPad"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Check that the MAC address resolves to a visible BLE device."""
    ble_device = bluetooth.async_ble_device_from_address(
        hass, data[CONF_MAC], connectable=True
    )
    if ble_device is None:
        raise CannotConnect
    return {CONF_MAC: ble_device.address, CONF_NAME: data[CONF_NAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PitPat WalkingPad."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step (manual MAC entry)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(dr.format_mac(info[CONF_MAC]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info[CONF_NAME], data=info)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery (auto-detected via service UUID)."""
        await self.async_set_unique_id(dr.format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()

        self._discovered = {
            CONF_MAC: discovery_info.address,
            CONF_NAME: discovery_info.name or "PitPat WalkingPad",
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm auto-discovered device."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered[CONF_NAME], data=self._discovered
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._discovered[CONF_NAME],
                "address": self._discovered[CONF_MAC],
            },
        )


class CannotConnect(HomeAssistantError):
    """Device not visible via Bluetooth."""
