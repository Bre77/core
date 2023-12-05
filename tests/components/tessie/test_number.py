"""Test the Tessie number platform."""

from homeassistant.components.tessie.const import TessieCategory
from homeassistant.core import HomeAssistant

from .common import TEST_STATE_OF_ALL_VEHICLES, setup_platform

STATES = TEST_STATE_OF_ALL_VEHICLES["results"][0]["last_state"]


async def test_numbers(hass: HomeAssistant) -> None:
    """Tests that the sensors are correct."""

    assert len(hass.states.async_all("number")) == 0

    await setup_platform(hass)

    assert len(hass.states.async_all("number")) == 3

    assert hass.states.get("number.test_charge_current").state == str(
        STATES[TessieCategory.CHARGE_STATE]["charge_current_request"]
    )

    assert hass.states.get("number.test_charge_limit").state == str(
        STATES[TessieCategory.CHARGE_STATE]["charge_limit_soc"]
    )

    assert hass.states.get("number.test_speed_limit").state == str(
        STATES[TessieCategory.VEHICLE_STATE]["speed_limit_mode"]["current_limit_mph"]
    )
