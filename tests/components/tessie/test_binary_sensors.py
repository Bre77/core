"""Test the Tessie sensor platform."""
import itertools

from homeassistant.components.tessie.binary_sensor import DESCRIPTIONS
from homeassistant.components.tessie.const import TessieCategory
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .common import TEST_STATE_OF_ALL_VEHICLES, setup_platform

STATES = TEST_STATE_OF_ALL_VEHICLES["results"][0]["last_state"]
SENSORS = len(list(itertools.chain.from_iterable(DESCRIPTIONS.values())))

OFFON = [STATE_OFF, STATE_ON]


async def test_binary_sensors(hass: HomeAssistant) -> None:
    """Tests that the sensors are correct."""

    assert len(hass.states.async_all("binary_sensor")) == 0

    await setup_platform(hass)

    assert len(hass.states.async_all("binary_sensor")) == SENSORS

    assert (hass.states.get("binary_sensor.test_battery_heater").state == STATE_ON) == (
        STATES[TessieCategory.CHARGE_STATE]["battery_heater_on"]
    )

    assert (hass.states.get("binary_sensor.test_charging").state == STATE_ON) == (
        STATES[TessieCategory.CHARGE_STATE]["charging_state"] == "Charging"
    )

    assert (
        hass.states.get("binary_sensor.test_auto_seat_climate_left").state == STATE_ON
    ) == (STATES[TessieCategory.CLIMATE_STATE]["auto_seat_climate_left"])
