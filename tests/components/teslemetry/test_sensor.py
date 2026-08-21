"""Test the Teslemetry sensor platform."""

from unittest.mock import AsyncMock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from tesla_fleet_api.exceptions import TeslaFleetError
from teslemetry_stream import Signal

from homeassistant.components.teslemetry.const import (
    CONF_SITE_ID,
    DOMAIN,
    SUBENTRY_TYPE_ENERGY_SITE,
)
from homeassistant.components.teslemetry.coordinator import (
    ENERGY_LIVE_INTERVAL,
    VEHICLE_INTERVAL,
)
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
    UnitOfPressure,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_conversion import PressureConverter

from . import assert_entities, assert_entities_alt, mock_config_entry, setup_platform
from .const import ENERGY_HISTORY_EMPTY, VEHICLE_DATA_ALT

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    mock_vehicle_data: AsyncMock,
    mock_legacy: AsyncMock,
) -> None:
    """Tests that the sensor entities with the legacy polling are correct."""

    freezer.move_to("2024-01-01 00:00:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    entry = await setup_platform(hass, [Platform.SENSOR])

    assert_entities(hass, entry.entry_id, entity_registry, snapshot)

    # Coordinator refresh
    mock_vehicle_data.return_value = VEHICLE_DATA_ALT
    freezer.tick(VEHICLE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert_entities_alt(hass, entry.entry_id, entity_registry, snapshot)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors_streaming(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_vehicle_data: AsyncMock,
    mock_add_listener: AsyncMock,
) -> None:
    """Tests that the sensor entities with streaming are correct."""

    freezer.move_to("2024-01-01 00:00:00+00:00")

    entry = await setup_platform(hass, [Platform.SENSOR])

    # Stream update
    mock_add_listener.send(
        {
            "vin": VEHICLE_DATA_ALT["response"]["vin"],
            "data": {
                Signal.DETAILED_CHARGE_STATE: "DetailedChargeStateCharging",
                Signal.BATTERY_LEVEL: 90,
                Signal.AC_CHARGING_ENERGY_IN: 10,
                Signal.AC_CHARGING_POWER: 2,
                Signal.CHARGING_CABLE_TYPE: None,
                Signal.TIME_TO_FULL_CHARGE: 0.166666667,
                Signal.MINUTES_TO_ARRIVAL: None,
            },
            "credits": {
                "type": "wake_up",
                "cost": 20,
                "name": "wake_up",
                "balance": 1980,
                "quota": {
                    "used": 212,
                    "fraction": 0.212,
                    "reset_at": "2026-07-10T00:00:00.000Z",
                },
            },
            "createdAt": "2024-10-04T10:45:17.537Z",
        }
    )
    await hass.async_block_till_done()

    # Balance-only credit events should not clear quota usage.
    mock_add_listener.send(
        {
            "credits": {"balance": 1980},
            "createdAt": "2024-10-04T10:45:18.537Z",
        }
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.teslemetry_command_quota_used").state == "21.2"

    # Reload the entry
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    # Assert the entities restored their values with concrete assertions
    assert hass.states.get("sensor.test_charging").state == "charging"
    assert hass.states.get("sensor.test_battery_level").state == "90"
    assert hass.states.get("sensor.test_charge_energy_added").state == "10"
    assert hass.states.get("sensor.test_charger_power").state == "2"
    assert hass.states.get("sensor.test_charge_cable").state == "unknown"
    assert hass.states.get("sensor.test_time_to_full_charge").state == "unknown"
    assert hass.states.get("sensor.test_time_to_arrival").state == "unknown"
    assert hass.states.get("sensor.teslemetry_command_credits").state == "1980"
    assert (quota_state := hass.states.get("sensor.teslemetry_command_quota_used"))
    assert quota_state.state == "21.2"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("signal", "entity_id", "streamed_value", "expected_state"),
    [
        (
            Signal.TPMS_PRESSURE_FL,
            "sensor.test_tire_pressure_front_left",
            2.7,
            # 2.7 atm independently hand-converted to bar (2.7 * 1.01325 = 2.735775)
            PressureConverter.convert(2.735775, UnitOfPressure.BAR, UnitOfPressure.PSI),
        ),
        (
            Signal.TPMS_PRESSURE_FR,
            "sensor.test_tire_pressure_front_right",
            2.7,
            # 2.7 atm independently hand-converted to bar (2.7 * 1.01325 = 2.735775)
            PressureConverter.convert(2.735775, UnitOfPressure.BAR, UnitOfPressure.PSI),
        ),
        (
            Signal.TPMS_PRESSURE_RL,
            "sensor.test_tire_pressure_rear_left",
            2.7,
            # 2.7 atm independently hand-converted to bar (2.7 * 1.01325 = 2.735775)
            PressureConverter.convert(2.735775, UnitOfPressure.BAR, UnitOfPressure.PSI),
        ),
        (
            Signal.TPMS_PRESSURE_RR,
            "sensor.test_tire_pressure_rear_right",
            2.7,
            # 2.7 atm independently hand-converted to bar (2.7 * 1.01325 = 2.735775)
            PressureConverter.convert(2.735775, UnitOfPressure.BAR, UnitOfPressure.PSI),
        ),
        (
            Signal.ISOLATION_RESISTANCE,
            "sensor.test_isolation_resistance",
            2.5,
            2.5,
        ),
    ],
    ids=["tpms_fl", "tpms_fr", "tpms_rl", "tpms_rr", "isolation_resistance"],
)
async def test_sensors_streaming_unit_conversion(
    hass: HomeAssistant,
    mock_vehicle_data: AsyncMock,
    mock_add_listener: AsyncMock,
    signal: Signal,
    entity_id: str,
    streamed_value: float,
    expected_state: float,
) -> None:
    """Test streamed TPMS pressure and isolation resistance are converted to their declared units."""

    await setup_platform(hass, [Platform.SENSOR])

    mock_add_listener.send(
        {
            "vin": VEHICLE_DATA_ALT["response"]["vin"],
            "data": {signal: streamed_value},
            "createdAt": "2024-10-04T10:45:17.537Z",
        }
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == pytest.approx(expected_state)


@pytest.mark.parametrize(
    ("key", "signal", "raw_value", "state"),
    [
        ("di_state_f", Signal.DI_STATE_F, "Standby", "standby"),
        ("di_state_r", Signal.DI_STATE_R, "Standby", "standby"),
        ("di_state_rel", Signal.DI_STATE_REL, "Standby", "standby"),
        ("di_state_rer", Signal.DI_STATE_RER, "Standby", "standby"),
        ("sentry_mode", Signal.SENTRY_MODE, "Armed", "armed"),
        (
            "forward_collision_warning",
            Signal.FORWARD_COLLISION_WARNING,
            "Average",
            "average",
        ),
        (
            "guest_mode_mobile_access_state",
            Signal.GUEST_MODE_MOBILE_ACCESS_STATE,
            "Authenticated",
            "authenticated",
        ),
        (
            "lane_departure_avoidance",
            Signal.LANE_DEPARTURE_AVOIDANCE,
            "Warning",
            "warning",
        ),
        ("powershare_status", Signal.POWERSHARE_STATUS, "Enabled", "enabled"),
        ("powershare_stop_reason", Signal.POWERSHARE_STOP_REASON, "Fault", "fault"),
        ("powershare_type", Signal.POWERSHARE_TYPE, "Home", "home"),
        (
            "scheduled_charging_mode",
            Signal.SCHEDULED_CHARGING_MODE,
            "StartAt",
            "start_at",
        ),
        ("speed_limit_warning", Signal.SPEED_LIMIT_WARNING, "Chime", "chime"),
        ("tonneau_tent_mode", Signal.TONNEAU_TENT_MODE, "Active", "active"),
        ("lights_turn_signal", Signal.LIGHTS_TURN_SIGNAL, "Left", "left"),
        ("hvac_power_state", Signal.HVAC_POWER, "On", "on"),
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_streaming_enum_none_clears_state(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_vehicle_data: AsyncMock,
    mock_add_listener: AsyncMock,
    key: str,
    signal: Signal,
    raw_value: str,
    state: str,
) -> None:
    """A None streamed value must clear the entity, not leave it stale."""
    await setup_platform(hass, [Platform.SENSOR])
    vin = VEHICLE_DATA_ALT["response"]["vin"]
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{vin}-{key}")
    assert entity_id is not None

    mock_add_listener.send(
        {
            "vin": vin,
            "data": {signal: raw_value},
            "createdAt": "2024-10-04T10:45:17.537Z",
        }
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == state

    mock_add_listener.send(
        {
            "vin": vin,
            "data": {signal: None},
            "createdAt": "2024-10-04T10:45:18.537Z",
        }
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_energy_history_no_time_series(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_energy_history: AsyncMock,
) -> None:
    """Test energy history coordinator when time_series is not a list."""
    # Mock energy history to return data without time_series as a list

    entry = await setup_platform(hass, [Platform.SENSOR])
    assert entry.state is ConfigEntryState.LOADED

    entity_id = "sensor.energy_site_battery_discharged"
    state = hass.states.get(entity_id)
    assert state.state == STATE_UNKNOWN

    mock_energy_history.return_value = ENERGY_HISTORY_EMPTY

    freezer.tick(VEHICLE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_UNAVAILABLE


SITE_ID = 123456
HOST = "192.168.91.1"
PASSWORD = "abcde"

# aiopowerwall's PowerwallClient parses the PEM at construction, so a paired
# site needs a real (if undersized, for speed) RSA key rather than fake bytes.
_TEST_RSA_KEY_PEM = rsa.generate_private_key(
    public_exponent=65537, key_size=1024
).private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)

# A local gateway live_status snapshot: distinct values for the nine locally
# supported keys, and None for every cloud-only key (as the local adapter
# actually returns) so a local success can be shown not to clobber them.
LOCAL_LIVE_STATUS = {
    "response": {
        "solar_power": 2000,
        "energy_left": 20000,
        "total_pack_energy": 40000,
        "percentage_charged": 80.0,
        "backup_capable": None,
        "battery_power": 3000,
        "load_power": 4000,
        "grid_status": "Active",
        "grid_services_active": None,
        "grid_power": 1000,
        "grid_services_power": None,
        "generator_power": 500,
        "island_status": "off_grid",
        "storm_mode_active": None,
        "timestamp": None,
        "wall_connectors": None,
    }
}

# entity_id -> local state string once the local snapshot has been applied.
_LOCAL_SENSOR_STATES = {
    "sensor.energy_site_solar_power": "2.0",
    "sensor.energy_site_energy_left": "20.0",
    "sensor.energy_site_total_pack_energy": "40.0",
    "sensor.energy_site_percentage_charged": "80.0",
    "sensor.energy_site_battery_power": "3.0",
    "sensor.energy_site_load_power": "4.0",
    "sensor.energy_site_grid_power": "1.0",
    "sensor.energy_site_generator_power": "0.5",
    "sensor.energy_site_island_status": "off_grid",
}


def _paired_entry() -> MockConfigEntry:
    """Return a config entry whose energy site is paired for local control."""
    entry = mock_config_entry()
    return MockConfigEntry(
        domain=entry.domain,
        version=entry.version,
        minor_version=entry.minor_version,
        unique_id=entry.unique_id,
        data=dict(entry.data),
        subentries_data=[
            ConfigSubentryData(
                subentry_type=SUBENTRY_TYPE_ENERGY_SITE,
                unique_id=str(SITE_ID),
                title="Energy Site",
                data={
                    CONF_SITE_ID: SITE_ID,
                    CONF_HOST: HOST,
                    CONF_PASSWORD: PASSWORD,
                },
            )
        ],
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_paired_site_live_sensors_read_local(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A paired site serves the nine live sensors from the local gateway.

    One local snapshot feeds all nine entities (no per-entity gateway request),
    and a local success must not clobber the cloud-only live fields with None.
    """
    entry = _paired_entry()
    entry.add_to_hass(hass)

    local_live = AsyncMock(return_value=LOCAL_LIVE_STATUS)
    with (
        patch(
            "homeassistant.components.teslemetry._async_get_rsa_key_pem",
            return_value=_TEST_RSA_KEY_PEM,
        ),
        patch(
            "aiopowerwall.energysite.PowerwallEnergySite.live_status",
            new=local_live,
        ),
        patch("homeassistant.components.teslemetry.PLATFORMS", [Platform.SENSOR]),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # One shared snapshot per refresh: a single interval tick makes exactly
        # one local gateway call regardless of how many entities read it.
        local_live.reset_mock()
        freezer.tick(ENERGY_LIVE_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert local_live.await_count == 1

    for entity_id, expected in _LOCAL_SENSOR_STATES.items():
        assert hass.states.get(entity_id).state == expected

    # grid_services_power is cloud-only; the local success returned None for it,
    # but its entity reads the separate cloud coordinator and keeps that value.
    assert hass.states.get("sensor.energy_site_grid_services_power").state == "0.0"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_paired_site_cloud_outage_keeps_local_sensors(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_live_status: AsyncMock,
) -> None:
    """A cloud outage leaves the nine local sensors available.

    The separate cloud coordinator fails and marks the cloud-only live entities
    unavailable, while the local coordinator keeps the nine local ones alive.
    """
    entry = _paired_entry()
    entry.add_to_hass(hass)

    local_live = AsyncMock(return_value=LOCAL_LIVE_STATUS)
    with (
        patch(
            "homeassistant.components.teslemetry._async_get_rsa_key_pem",
            return_value=_TEST_RSA_KEY_PEM,
        ),
        patch(
            "aiopowerwall.energysite.PowerwallEnergySite.live_status",
            new=local_live,
        ),
        patch("homeassistant.components.teslemetry.PLATFORMS", [Platform.SENSOR]),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Cloud live_status now fails; local keeps working.
        mock_live_status.side_effect = TeslaFleetError
        freezer.tick(ENERGY_LIVE_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    for entity_id, expected in _LOCAL_SENSOR_STATES.items():
        assert hass.states.get(entity_id).state == expected

    # Cloud-only live entity goes unavailable with the cloud coordinator.
    assert (
        hass.states.get("sensor.energy_site_grid_services_power").state
        == STATE_UNAVAILABLE
    )
