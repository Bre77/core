"""Test the Tessie number platform."""

from unittest.mock import patch

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.components.tessie.const import TessieCategory
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from .common import TEST_RESPONSE, TEST_VEHICLE_STATE_ONLINE, setup_platform


async def test_numbers(hass: HomeAssistant) -> None:
    """Tests that the sensors are correct."""

    assert len(hass.states.async_all("number")) == 0

    await setup_platform(hass)

    assert len(hass.states.async_all("number")) == 3

    assert hass.states.get("number.test_charge_current").state == str(
        TEST_VEHICLE_STATE_ONLINE[TessieCategory.CHARGE_STATE]["charge_current_request"]
    )

    assert hass.states.get("number.test_charge_limit").state == str(
        TEST_VEHICLE_STATE_ONLINE[TessieCategory.CHARGE_STATE]["charge_limit_soc"]
    )

    assert hass.states.get("number.test_speed_limit").state == str(
        TEST_VEHICLE_STATE_ONLINE[TessieCategory.VEHICLE_STATE]["speed_limit_mode"][
            "current_limit_mph"
        ]
    )

    # Test number set value "homeassistant.components.tessie.entity.TessieEntity.run",
    entity_id = "number.test_charge_current"
    with patch(
        "homeassistant.components.tessie.number.set_charge_limit",
        return_value=TEST_RESPONSE,
    ) as mock_set:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: [entity_id], "value": 16},
            blocking=True,
        )
        mock_set.assert_called_once()
