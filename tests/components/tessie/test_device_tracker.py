"""Test the Tessie device tracker platform."""
from unittest.mock import patch

import pytest

from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.components.tessie.const import DOMAIN, TessieGroup
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir

from .common import (
    ERROR_TIMEOUT,
    ERROR_UNKNOWN,
    ERROR_VIRTUAL_KEY,
    TEST_STATE_OF_ALL_VEHICLES,
    setup_platform,
)

STATES = TEST_STATE_OF_ALL_VEHICLES["results"][0]["last_state"]


async def test_device_tracker(hass: HomeAssistant) -> None:
    """Tests that the device trackers are correct."""

    assert len(hass.states.async_all(DEVICE_TRACKER_DOMAIN)) == 0

    await setup_platform(hass)

    assert len(hass.states.async_all(DEVICE_TRACKER_DOMAIN)) == 1

    entity_id = "climate.test_climate"
    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF
    assert (
        state.attributes.get(ATTR_MIN_TEMP)
        == STATES[TessieGroup.CLIMATE_STATE]["min_avail_temp"]
    )
    assert (
        state.attributes.get(ATTR_MAX_TEMP)
        == STATES[TessieGroup.CLIMATE_STATE]["max_avail_temp"]
    )

    # Test setting climate on
    with patch(
        "homeassistant.components.tessie.climate.start_climate_preconditioning"
    ) as mock_set:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.HEAT_COOL},
            blocking=True,
        )
        mock_set.assert_called_once()

    # Test setting climate temp
    with patch("homeassistant.components.tessie.climate.set_temperature") as mock_set:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 20},
            blocking=True,
        )
        mock_set.assert_called_once()

    # Test setting climate preset
    with patch(
        "homeassistant.components.tessie.climate.set_climate_keeper_mode"
    ) as mock_set:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_PRESET_MODE: KEEPER_NAMES[1]},
            blocking=True,
        )
        mock_set.assert_called_once()

    # Test setting climate off
    with patch("homeassistant.components.tessie.climate.stop_climate") as mock_set:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.OFF},
            blocking=True,
        )
        mock_set.assert_called_once()


async def test_errors(hass: HomeAssistant) -> None:
    """Tests virtual key error is handled."""

    await setup_platform(hass)
    entity_id = "climate.test_climate"

    # Test setting climate on with virtual key error
    with patch(
        "homeassistant.components.tessie.climate.start_climate_preconditioning",
        side_effect=ERROR_VIRTUAL_KEY,
    ) as mock_set, pytest.raises(HomeAssistantError) as error:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_set.assert_called_once()
        assert error.from_exception == ERROR_VIRTUAL_KEY

    issue_reg = ir.async_get(hass)
    assert issue_reg.async_get_issue(DOMAIN, "virtual_key")

    # Test setting climate on with virtual key error
    with patch(
        "homeassistant.components.tessie.climate.start_climate_preconditioning",
        side_effect=ERROR_TIMEOUT,
    ) as mock_set, pytest.raises(HomeAssistantError) as error:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_set.assert_called_once()
        assert error.from_exception == ERROR_TIMEOUT

    # Test setting climate on with virtual key error
    with patch(
        "homeassistant.components.tessie.climate.start_climate_preconditioning",
        side_effect=ERROR_UNKNOWN,
    ) as mock_set, pytest.raises(HomeAssistantError) as error:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
        mock_set.assert_called_once()
        assert error.from_exception == ERROR_UNKNOWN
