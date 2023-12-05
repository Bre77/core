"""Test the Tessie device tracker platform."""


from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.components.tessie.const import TessieCategory
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant

from .common import TEST_STATE_OF_ALL_VEHICLES, setup_platform

STATES = TEST_STATE_OF_ALL_VEHICLES["results"][0]["last_state"]


async def test_device_tracker(hass: HomeAssistant) -> None:
    """Tests that the device trackers are correct."""

    assert len(hass.states.async_all(DEVICE_TRACKER_DOMAIN)) == 0

    await setup_platform(hass)

    assert len(hass.states.async_all(DEVICE_TRACKER_DOMAIN)) == 2

    entity_id = "device_tracker.test_location"
    state = hass.states.get(entity_id)
    assert (
        state.attributes.get(ATTR_LATITUDE)
        == STATES[TessieCategory.DRIVE_STATE]["latitude"]
    )
    assert (
        state.attributes.get(ATTR_LONGITUDE)
        == STATES[TessieCategory.DRIVE_STATE]["longitude"]
    )

    entity_id = "device_tracker.test_route"
    state = hass.states.get(entity_id)
    assert (
        state.attributes.get(ATTR_LATITUDE)
        == STATES[TessieCategory.DRIVE_STATE]["active_route_latitude"]
    )
    assert (
        state.attributes.get(ATTR_LONGITUDE)
        == STATES[TessieCategory.DRIVE_STATE]["active_route_longitude"]
    )
