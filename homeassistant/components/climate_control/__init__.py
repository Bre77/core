"""Climate Control climate integration."""

from datetime import timedelta
import logging

from homeassistant.const import CONF_ENTITY_ID

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    CONF_ZONES,
    DOMAIN,
)

PLATFORMS = ["climate"]  # , "sensor"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    """Set up Climate Control config."""
    climate_entity = entry.data[CONF_CLIMATE_ENTITY]
    zones = entry.data[CONF_ZONES]
    return True


async def async_unload_entry(hass, entry):
    """Unload Climate Control Config."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
