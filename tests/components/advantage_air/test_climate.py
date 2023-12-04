"""Test the Advantage Air Climate Platform."""

from advantage_air import ApiError
import pytest

from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_LOW,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    HVACMode,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from . import add_mock_config, patch_update


@pytest.mark.usefixtures("mock_get", "mock_update")
async def test_climate_myzone_main(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_get, mock_update
) -> None:
    """Test climate platform main entity."""

    await add_mock_config(hass)

    # Test MyZone main climate entity
    entity_id = "climate.myzone"
    state = hass.states.get(entity_id)
    assert state
    assert state.state == HVACMode.FAN_ONLY
    assert state.attributes.get(ATTR_MIN_TEMP) == 16
    assert state.attributes.get(ATTR_MAX_TEMP) == 32
    assert state.attributes.get(ATTR_TEMPERATURE) == 24
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 25

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1"

    # Test setting HVAC Mode

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.FAN_ONLY},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Turning Off with HVAC Mode
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_FAN_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_FAN_MODE: FAN_LOW},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test changing Temperature
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 25},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Turning On
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Turning Off
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: [entity_id]},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()


async def test_climate_myzone_zone(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_get, mock_update
) -> None:
    """Test climate platform myzone zone entity."""

    await add_mock_config(hass)

    # Test Climate Zone Entity
    entity_id = "climate.myzone_zone_open_with_sensor"
    state = hass.states.get(entity_id)
    assert state
    assert state.attributes.get(ATTR_MIN_TEMP) == 16
    assert state.attributes.get(ATTR_MAX_TEMP) == 32
    assert state.attributes.get(ATTR_TEMPERATURE) == 24
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 25

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac1-z01"

    # Test Climate Zone On
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.FAN_ONLY},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    # Test Climate Zone Off
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: [entity_id], ATTR_TEMPERATURE: 25},
        blocking=True,
    )
    mock_update.assert_called_once()
    mock_update.reset_mock()


async def test_climate_myauto_main(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_get, mock_update
) -> None:
    """Test climate platform zone entity."""

    await add_mock_config(hass)

    # Test MyAuto Climate Entity
    entity_id = "climate.myauto"
    state = hass.states.get(entity_id)
    assert state
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 20
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 24

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "uniqueid-ac3"

    with patch_update() as mock_update:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: [entity_id],
                ATTR_TARGET_TEMP_LOW: 21,
                ATTR_TARGET_TEMP_HIGH: 23,
            },
            blocking=True,
        )
        mock_update.assert_called_once()


async def test_climate_async_failed_update(hass: HomeAssistant, mock_get) -> None:
    """Test climate change failure."""

    with patch_update(side_effect=ApiError) as mock_update, pytest.raises(
        HomeAssistantError
    ):
        await add_mock_config(hass)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ["climate.myzone"], ATTR_TEMPERATURE: 25},
            blocking=True,
        )
        mock_update.assert_called_once()
