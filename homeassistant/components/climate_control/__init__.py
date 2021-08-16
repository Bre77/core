"""Climate Control climate integration."""

from datetime import timedelta
import logging

from homeassistant.const import CONF_ENTITY_ID

from .const import DOMAIN

PLATFORMS = ["climate"]  # , "sensor"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    """Set up Climate Control config."""
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass, entry):
    """Unload Climate Control Config."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
