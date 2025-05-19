"""Test the Teslemetry calendar platform."""

from datetime import datetime
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.calendar import (
    DOMAIN as CALENDAR_DOMAIN,
    EVENT_END_DATETIME,
    EVENT_START_DATETIME,
    SERVICE_GET_EVENTS,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from . import assert_entities, setup_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_calandar(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    mock_legacy: AsyncMock,
) -> None:
    """Tests that the calendar entity is correct."""

    TZ = dt_util.get_default_time_zone()
    freezer.move_to(datetime(2024, 1, 1, 10, 0, 0, tzinfo=TZ))

    entry = await setup_platform(hass, [Platform.CALENDAR])

    assert_entities(hass, entry.entry_id, entity_registry, snapshot)


@pytest.mark.parametrize(
    "entity_id",
    [
        "calendar.test_precondition_schedule",
        "calendar.test_charging_schedule",
        "calendar.energy_site_buy_tariff",
        "calendar.energy_site_sell_tariff",
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_calandar_events(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    mock_legacy: AsyncMock,
    entity_id: str,
) -> None:
    """Tests that the calendar entity is correct."""

    TZ = dt_util.get_default_time_zone()
    freezer.move_to(datetime(2024, 1, 1, 10, 0, 0, tzinfo=TZ))

    await setup_platform(hass, [Platform.CALENDAR])
    result = await hass.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            ATTR_ENTITY_ID: [entity_id],
            EVENT_START_DATETIME: dt_util.parse_datetime("2024-01-01T00:00:00Z"),
            EVENT_END_DATETIME: dt_util.parse_datetime("2024-01-07T00:00:00Z"),
        },
        blocking=True,
        return_response=True,
    )
    assert result == snapshot()


# Test cases for TeslemetryTariffSchedule.event
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_tariff_schedule_event_no_seasons(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_legacy: AsyncMock,
) -> None:
    """Test TeslemetryTariffSchedule event property when no seasons are defined."""
    TZ = dt_util.get_default_time_zone()
    freezer.move_to(datetime(2024, 1, 1, 10, 0, 0, tzinfo=TZ))
    await setup_platform(hass, [Platform.CALENDAR])
    entity = hass.states.get("calendar.energy_site_buy_tariff")
    assert entity is not None

    # Mock coordinator data to have no seasons
    coordinator = hass.data[CALENDAR_DOMAIN]["teslemetry_123456"].energysites[0].info_coordinator
    original_data = coordinator.data
    coordinator.data = {
        **coordinator.data,
        "tariff_content_v2_seasons": {},
        "tariff_content_v2_energy_charges": {},
    }

    calendar_entity = CALENDAR_DOMAIN.get_entity("calendar.energy_site_buy_tariff")
    assert calendar_entity.event is None

    # Restore original data
    coordinator.data = original_data


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_tariff_schedule_event_outside_season(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_legacy: AsyncMock,
) -> None:
    """Test TeslemetryTariffSchedule event property when now is outside any season."""
    TZ = dt_util.get_default_time_zone()
    # Date outside the "Summer" season defined in fixtures (Jan 1 to Dec 31)
    # Forcing a scenario where no season applies by using a date far in the past
    # or by setting up specific non-overlapping seasons if necessary.
    # The current fixture has a Summer season for the whole year, so we'll mock it.

    await setup_platform(hass, [Platform.CALENDAR])
    entity = hass.states.get("calendar.energy_site_buy_tariff")
    assert entity is not None

    coordinator = hass.data[CALENDAR_DOMAIN]["teslemetry_123456"].energysites[0].info_coordinator
    original_data = coordinator.data
    mock_seasons = {
        "Spring": {
            "fromMonth": 3, "fromDay": 1, "toMonth": 5, "toDay": 31,
            "tou_periods": {
                "MORNING": {"periods": [{"fromDayOfWeek": 0, "toDayOfWeek": 6, "fromHour": 7, "toHour": 11}]}
            }
        }
    }
    mock_charges = {"Spring": {"rates": {"MORNING": 0.15}}}
    coordinator.data = {
        **coordinator.data,
        "tariff_content_v2_seasons": mock_seasons,
        "tariff_content_v2_energy_charges": mock_charges,
    }
    # Move to a date outside "Spring"
    freezer.move_to(datetime(2024, 1, 1, 10, 0, 0, tzinfo=TZ))
    calendar_entity = CALENDAR_DOMAIN.get_entity("calendar.energy_site_buy_tariff")
    assert calendar_entity.event is None

    # Restore original data
    coordinator.data = original_data


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_tariff_schedule_event_year_spanning_season(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_legacy: AsyncMock,
) -> None:
    """Test TeslemetryTariffSchedule event for year-spanning seasons."""
    TZ = dt_util.get_default_time_zone()
    await setup_platform(hass, [Platform.CALENDAR])
    entity = hass.states.get("calendar.energy_site_buy_tariff")
    assert entity is not None

    coordinator = hass.data[CALENDAR_DOMAIN]["teslemetry_123456"].energysites[0].info_coordinator
    original_data = coordinator.data
    mock_seasons_spanning = {
        "Winter": {
            "fromMonth": 11, "fromDay": 1, "toMonth": 2, "toDay": 28, # Nov 1 to Feb 28
            "tou_periods": {
                "PEAK_WINTER": {"periods": [{"fromDayOfWeek": 0, "toDayOfWeek": 6, "fromHour": 17, "toHour": 20}]}
            }
        }
    }
    mock_charges_spanning = {"Winter": {"rates": {"PEAK_WINTER": 0.30}}}
    coordinator.data = {
        **coordinator.data,
        "tariff_content_v2_seasons": mock_seasons_spanning,
        "tariff_content_v2_energy_charges": mock_charges_spanning,
    }

    calendar_entity = CALENDAR_DOMAIN.get_entity("calendar.energy_site_buy_tariff")

    # Test within December part of the season
    freezer.move_to(datetime(2023, 12, 15, 18, 0, 0, tzinfo=TZ)) # Dec 15th, 6 PM
    event_dec = calendar_entity.event
    assert event_dec is not None
    assert event_dec.summary == "0.3/kWh"
    assert event_dec.start == datetime(2023, 12, 15, 17, 0, 0, tzinfo=TZ)
    assert event_dec.end == datetime(2023, 12, 15, 20, 0, 0, tzinfo=TZ)

    # Test within January part of the season
    freezer.move_to(datetime(2024, 1, 15, 18, 0, 0, tzinfo=TZ)) # Jan 15th, 6 PM
    event_jan = calendar_entity.event
    assert event_jan is not None
    assert event_jan.summary == "0.3/kWh"
    assert event_jan.start == datetime(2024, 1, 15, 17, 0, 0, tzinfo=TZ)
    assert event_jan.end == datetime(2024, 1, 15, 20, 0, 0, tzinfo=TZ)

    # Test outside the year-spanning season (e.g. March)
    freezer.move_to(datetime(2024, 3, 15, 18, 0, 0, tzinfo=TZ))
    assert calendar_entity.event is None

    # Restore original data
    coordinator.data = original_data


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_tariff_schedule_event_boundary_conditions(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_legacy: AsyncMock,
) -> None:
    """Test TeslemetryTariffSchedule event at boundary conditions."""
    TZ = dt_util.get_default_time_zone()
    await setup_platform(hass, [Platform.CALENDAR])
    entity = hass.states.get("calendar.energy_site_buy_tariff")
    assert entity is not None

    coordinator = hass.data[CALENDAR_DOMAIN]["teslemetry_123456"].energysites[0].info_coordinator
    original_data = coordinator.data
    mock_seasons_boundary = {
        "MidSeason": {
            "fromMonth": 6, "fromDay": 1, "toMonth": 8, "toDay": 31, # June 1 to Aug 31
            "tou_periods": {
                "DAYTIME": {"periods": [{"fromDayOfWeek": 0, "toDayOfWeek": 6, "fromHour": 9, "toHour": 17}]}
            }
        }
    }
    mock_charges_boundary = {"MidSeason": {"rates": {"DAYTIME": 0.12}}}
    coordinator.data = {
        **coordinator.data,
        "tariff_content_v2_seasons": mock_seasons_boundary,
        "tariff_content_v2_energy_charges": mock_charges_boundary,
    }
    calendar_entity = CALENDAR_DOMAIN.get_entity("calendar.energy_site_buy_tariff")

    # Exactly at the start of a season and period
    freezer.move_to(datetime(2024, 6, 1, 9, 0, 0, tzinfo=TZ))
    event_start = calendar_entity.event
    assert event_start is not None
    assert event_start.summary == "0.12/kWh"
    assert event_start.start == datetime(2024, 6, 1, 9, 0, 0, tzinfo=TZ)

    # Exactly at the end of a period (event should be None as 'now' is not < end_time)
    # The current logic is `start_time < now < end_time`. So at exactly end_time, it should be None.
    freezer.move_to(datetime(2024, 6, 1, 17, 0, 0, tzinfo=TZ))
    assert calendar_entity.event is None

    # Just before the end of a period
    freezer.move_to(datetime(2024, 6, 1, 16, 59, 59, tzinfo=TZ))
    event_just_before_end = calendar_entity.event
    assert event_just_before_end is not None
    assert event_just_before_end.summary == "0.12/kWh"

    # Exactly at the end of a season (should be None)
    # Season ends Aug 31, so Aug 31 23:59:59 is in, Sep 1 00:00:00 is out.
    # Test with a time within the last period of the season, but on the last day.
    freezer.move_to(datetime(2024, 8, 31, 10, 0, 0, tzinfo=TZ))
    event_last_day_season = calendar_entity.event
    assert event_last_day_season is not None
    assert event_last_day_season.summary == "0.12/kWh"

    # Move to the day after the season ends
    freezer.move_to(datetime(2024, 9, 1, 10, 0, 0, tzinfo=TZ))
    assert calendar_entity.event is None


    # Restore original data
    coordinator.data = original_data

# Ensure TariffPeriod class name is correct in any direct usage in tests if any (not directly used in these new tests)
# The snapshot tests `test_calandar` and `test_calandar_events` will cover entity states and event data
# which indirectly rely on TariffPeriod, but the class name change was in the main code.
# These new tests mock the coordinator data, so direct usage of TariffPeriod is not here.
