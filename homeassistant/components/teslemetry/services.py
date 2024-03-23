import logging
from typing import Any, Dict
import voluptuous as vol


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import (
    aiohttp_client,
    config_validation as cv,
    device_registry as dr,
)
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


def async_get_device_for_service_call(
    hass: HomeAssistant, call: ServiceCall
) -> dr.DeviceEntry:
    """Get the device entry related to a service call."""
    device_id = call.data[CONF_DEVICE_ID]
    device_registry = dr.async_get(hass)

    if (device_entry := device_registry.async_get(device_id)) is None:
        raise ServiceValidationError(f"Invalid Tessie device ID: {device_id}")
    return device_entry


def async_get_entry_for_device(
    hass: HomeAssistant, device_entry: dr.DeviceEntry
) -> ConfigEntry:
    """Get the config entry related to a device entry."""

    for entry_id in device_entry.config_entries:
        if (entry := hass.config_entries.async_get_entry(entry_id)) is None:
            continue
        if entry.domain == DOMAIN:
            return entry

    raise ServiceValidationError(f"No config entry for device ID: {device_entry.id}")


async def async_register_services(hass: HomeAssistant) -> bool:
    """Set up the Tessie integration."""

    async def service_share(call: ServiceCall) -> None:
        """Share the value with a vehicle."""
        device = async_get_device_for_service_call(hass, call)
        entry = async_get_entry_for_device(hass, device)

        assert device.serial_number is not None

        try:
            response = await share(
                session=session,
                vin=device.serial_number,
                api_key=entry.data[CONF_ACCESS_TOKEN],
                value=call.data[TESSIE_VALUE],
                locale=call.data[TESSIE_LOCALE],
            )
        except ClientResponseError as e:
            raise HomeAssistantError from e
        if response["result"] is False:
            raise HomeAssistantError(
                response.get("reason"), "An unknown issue occurred"
            )

    hass.services.async_register(
        DOMAIN,
        TESSIE_SERVICE_SHARE,
        service_share,
        schema=vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): cv.string,
                vol.Required(TESSIE_VALUE): cv.string,
                vol.Optional(TESSIE_LOCALE, default=TESSIE_LOCALE_DEFAULT): cv.string,
            }
        ),
    )
    return True
