"""Tessie integration."""
from http import HTTPStatus

from aiohttp import ClientError, ClientResponseError
from tessie_api import get_state_of_all_vehicles

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import TessieDataUpdateCoordinator

TESSIE_SYNC_INTERVAL = 15
PLATFORMS = [
    Platform.SENSOR,
    Platform.CLIMATE,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]


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
        raise ConfigEntryNotReady from e
    except ClientError as e:
        raise ConfigEntryNotReady from e

    coordinators = [
        TessieDataUpdateCoordinator(
            hass,
            api_key=api_key,
            vin=vehicle["vin"],
            data=vehicle["last_state"],
        )
        for vehicle in vehicles["results"]
    ]

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Tessie Config."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
