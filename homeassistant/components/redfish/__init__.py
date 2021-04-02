"""Redfish integration."""

import asyncio
from datetime import timedelta
import logging

from aiohttp import BasicAuth

from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

REDFISH_SYNC_INTERVAL = 15
PLATFORMS = ["switch", "sensor", "binary_sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up Redfish integration."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass, entry):
    """Set up Redfish config."""
    url = entry.data[CONF_URL]
    auth = BasicAuth(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    ids = entry.data["ids"]

    session = async_get_clientsession(hass, verify_ssl=False)

    async def async_get():
        data = {}
        for id in ids:
            data[id] = {}
            # System data
            async with session.get(f"{url}/redfish/v1/Systems/{id}", auth=auth) as resp:
                if resp.status >= 400:
                    _LOGGER.error(f"Failed to get {resp.url} with status {resp.status}")
                    raise UpdateFailed(resp.status)
                data[id]["Systems"] = await resp.json()

            # Chassis PowerControl data
            async with session.get(
                f"{url}/redfish/v1/Chassis/{id}/Power/PowerControl", auth=auth
            ) as resp:
                if resp.status >= 400:
                    _LOGGER.error(f"Failed to get {resp.url} with status {resp.status}")
                    raise UpdateFailed(resp.status)
                data[id]["PowerControl"] = await resp.json()

            # Chassis Thermal data
            async with session.get(
                f"{url}/redfish/v1/Chassis/{id}/Thermal", auth=auth
            ) as resp:
                if resp.status >= 400:
                    _LOGGER.error(f"Failed to get {resp.url} with status {resp.status}")
                    raise UpdateFailed(resp.status)
                data[id]["Thermal"] = await resp.json()
        return data

    async def async_change(endpoint, payload):
        print(f"{url}{endpoint}")
        async with session.post(f"{url}{endpoint}", json=payload, auth=auth) as resp:
            print(await resp.text())
        # await coordinator.async_refresh()
        return True

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Redfish",
        update_method=async_get,
        update_interval=timedelta(seconds=REDFISH_SYNC_INTERVAL),
    )

    await coordinator.async_refresh()

    if not coordinator.data:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "async_change": async_change,
    }

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass, entry):
    """Unload Redfish Config."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
