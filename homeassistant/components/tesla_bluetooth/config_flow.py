"""Config flow for Tesla Bluetooth integration."""

from __future__ import annotations

import dataclasses
from typing import Any

from bleak import BleakClient
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DEVICE_NAME_UUID, DOMAIN, LOGGER, MANUFACTURER_ID, SERVICE_UUIDS

# AirthingsDevice


@dataclasses.dataclass
class Discovery:
    """A discovered bluetooth device."""

    name: str
    discovery_info: BluetoothServiceInfo
    # device: AirthingsDevice


def validate(name: str) -> bool:
    """Validate the name of a Tesla device."""
    return len(name) == 18 and name[0] == "S" and name[17] == "C"


class TeslaBluetoothConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla Bluetooth."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: Discovery | None = None
        self._discovered_devices: dict[str, Discovery] = {}

    async def _get_name(self, discovery_info: BluetoothServiceInfo) -> str:
        return discovery_info.address

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfo
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        if not validate(discovery_info.name):
            return self.async_abort(reason="not_tesla_device")

        LOGGER.debug(
            "Discovered BT device: %s @ %s", discovery_info.name, discovery_info.address
        )
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        name = await self._get_name(discovery_info)
        self.context["title_placeholders"] = {"name": name}
        self._discovered_device = Discovery(
            name=await self._get_name(discovery_info), discovery_info=discovery_info
        )

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""

        assert self._discovered_device is not None

        if user_input is not None:
            return self.async_create_entry(title=self._discovered_device.name, data={})

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=self.context["title_placeholders"],
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device."""

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured
            self._discovered_device = self._discovered_devices[address]

            return self.async_create_entry(title=self._discovered_device.name, data={})

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue

            if discovery_info.manufacturer_id != MANUFACTURER_ID:
                continue

            if not validate(discovery_info.name):
                continue

            if not any(uuid in SERVICE_UUIDS for uuid in discovery_info.service_uuids):
                continue

            name = await self._get_name(discovery_info)
            self._discovered_devices[address] = Discovery(name, discovery_info)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        print(self._discovered_devices)
        titles = {
            address: discovery.name
            for (address, discovery) in self._discovered_devices.items()
        }
        print(titles)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(titles),
                },
            ),
        )
