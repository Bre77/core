"""Test the Tessie switch platform."""
from homeassistant.components.tessie.switch import DESCRIPTIONS
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant

from .common import TEST_VEHICLE_STATE_ONLINE, setup_platform


async def test_switches(hass: HomeAssistant) -> None:
    """Tests that the switches are correct."""

    assert len(hass.states.async_all("switch")) == 0

    await setup_platform(hass)

    assert len(hass.states.async_all("switch")) == len(DESCRIPTIONS)

    assert (hass.states.get("switch.test_charge").state == STATE_ON) == (
        TEST_VEHICLE_STATE_ONLINE["charge_state"]["charge_enable_request"]
    )
    assert (hass.states.get("switch.test_sentry_mode").state == STATE_ON) == (
        TEST_VEHICLE_STATE_ONLINE["vehicle_state"]["sentry_mode"]
    )
