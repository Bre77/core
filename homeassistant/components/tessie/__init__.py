"""Tessie integration."""
from http import HTTPStatus
import logging
import voluptuous as vol

from aiohttp import ClientError, ClientResponseError
from tessie_api import get_state_of_all_vehicles, share

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform, CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv, entity_platform

from .const import DOMAIN, TESSIE_SERVICE_SHARE
from .coordinator import TessieStateUpdateCoordinator
from .models import TessieVehicle

TESSIE_SERVICE_SHARE_SCHEMA = {vol.Required(CONF_DEVICE_ID): cv.string, vol.Required("value"): cv.string}

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

@callback
def async_get_entry_for_service_call(
    hass: HomeAssistant, call: ServiceCall
) -> ConfigEntry:
    """Get the controller related to a service call (by device ID)."""
    device_id = call.data[CONF_DEVICE_ID]
    device_registry = dr.async_get(hass)

    if (device_entry := device_registry.async_get(device_id)) is None:
        raise ValueError(f"Invalid RainMachine device ID: {device_id}")

    for entry_id in device_entry.config_entries:
        if (entry := hass.config_entries.async_get_entry(entry_id)) is None:
            continue
        if entry.domain == DOMAIN:
            return entry

    raise ValueError(f"No controller for device ID: {device_id}")



async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the Tessie integration."""

    session = async_get_clientsession(hass)
    locale = "en-us"
    async def share(value: str) -> str:
        response = await share(session, vin, api_key, value, locale)
        return "Success" if response.result is True else response.get("reason","An unknown issue occurred")

    hass.services.async_register(
        DOMAIN,
        TESSIE_SERVICE_SHARE,
        share,
        TESSIE_SERVICE_SHARE_SCHEMA
    )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tessie config."""
    api_key = entry.data[CONF_ACCESS_TOKEN]

    try:
        vehicles = await get_state_of_all_vehicles(
            session=async_get_clientsession(hass),
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
