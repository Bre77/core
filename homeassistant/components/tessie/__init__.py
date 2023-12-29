"""Tessie integration."""
from http import HTTPStatus
import logging

from aiohttp import ClientError, ClientResponseError
from tessie_api import get_state_of_all_vehicles, share
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import (
    aiohttp_client,
    config_validation as cv,
    device_registry as dr,
)
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, TESSIE_SERVICE_SHARE
from .coordinator import TessieStateUpdateCoordinator
from .models import TessieVehicle

TESSIE_VALUE = "value"
TESSIE_LOCALE = "locale"
TESSIE_LOCALE_DEFAULT = "en-US"
TESSIE_SERVICE_SHARE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(TESSIE_VALUE): cv.string,
        vol.Optional(TESSIE_LOCALE, default=TESSIE_LOCALE_DEFAULT): cv.string,
    }
)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=True)


def async_get_device_for_service_call(
    hass: HomeAssistant, call: ServiceCall
) -> dr.DeviceEntry:
    """Get the device entry related to a service call."""
    device_id = call.data[CONF_DEVICE_ID]
    device_registry = dr.async_get(hass)

    if (device_entry := device_registry.async_get(device_id)) is None:
        raise ValueError(f"Invalid Tessie device ID: {device_id}")
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

    raise ValueError(f"No controller for device ID: {device_entry.id}")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tessie integration."""

    session = aiohttp_client.async_get_clientsession(hass)

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
        DOMAIN, TESSIE_SERVICE_SHARE, service_share, schema=TESSIE_SERVICE_SHARE_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tessie config."""
    api_key = entry.data[CONF_ACCESS_TOKEN]

    try:
        vehicles = await get_state_of_all_vehicles(
            session=aiohttp_client.async_get_clientsession(hass),
            api_key=api_key,
            only_active=True,
        )
    except ClientResponseError as e:
        if e.status == HTTPStatus.UNAUTHORIZED:
            raise ConfigEntryAuthFailed from e
        _LOGGER.error("Setup failed, unable to connect to Tessie: %s", e)
        return False
    except ClientError as e:
        raise ConfigEntryNotReady from e

    data = [
        TessieVehicle(
            state_coordinator=TessieStateUpdateCoordinator(
                hass,
                api_key=api_key,
                vin=vehicle["vin"],
                data=vehicle["last_state"],
            )
        )
        for vehicle in vehicles["results"]
        if vehicle["last_state"] is not None
    ]

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Tessie Config."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
