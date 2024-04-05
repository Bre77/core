"""Test the Teslemetry services."""

from homeassistant.components.teslemetry.const import DOMAIN
from homeassistant.components.teslemetry.services import GPS
from homeassistant.const import ATTR_DEVICE_ID, CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from . import setup_platform


async def test_services(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> None:
    """Tests that the climate entity is correct."""

    await setup_platform(hass, [Platform.CLIMATE])
    device = device_registry.async_get_device((DOMAIN, "VINVINVIN"))

    await hass.services.async_call(
        DOMAIN,
        "navigate_gps_request",
        {ATTR_DEVICE_ID: device.id, GPS: {CONF_LATITUDE: 0, CONF_LONGITUDE: 0}},
        blocking=True,
    )
