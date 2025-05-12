"""Sensor platform for Tesla Bluetooth integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import chain
from typing import Any

from tesla_fleet_api.tesla.vehicle.bluetooth import (
    ChargeState,
    ClimateState,
    DriveState,
    TirePressureState,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TeslaBluetoothConfigEntry
from .entity import (
    TeslaBluetoothChargeEntity,
    TeslaBluetoothClimateEntity,
    TeslaBluetoothDriveEntity,
    TeslaBluetoothEntity,
    TeslaBluetoothTirePressureEntity,
)
from .models import TeslaBluetoothData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothChargeSensorEntityDescription(SensorEntityDescription):
    """Describes Tesla Bluetooth charge sensor entity."""

    value_fn: Callable[[ChargeState], Any] = lambda _: None


CHARGE_DESCRIPTIONS: tuple[TeslaBluetoothChargeSensorEntityDescription, ...] = (
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_battery_range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.battery_range,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_est_battery_range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.est_battery_range,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_ideal_battery_range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.ideal_battery_range,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_battery_level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.battery_level,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_usable_battery_level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.usable_battery_level,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_charge_energy_added",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda x: x.charge_energy_added,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_charge_rate",
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.charge_rate_mph,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_charger_actual_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda x: x.charger_actual_current,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_charger_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=lambda x: x.charger_power,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_charger_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda x: x.charger_voltage,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_minutes_to_full_charge",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.minutes_to_full_charge,
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_conn_charge_cable",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=[
            "tesla",
            "j1772",
            "ccs1",
            "ccs2",
            "type2",
            "nacs",
            "gbt",
            "unknown",
            "none",
        ],
        value_fn=lambda x: str(x.conn_charge_cable).lower().replace("/", "")
        if x.conn_charge_cable
        else "none",
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_fast_charger_type",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["tesla", "ccs", "nacs", "chademo", "none"],
        value_fn=lambda x: str(x.fast_charger_type).lower()
        if x.fast_charger_type
        else "none",
    ),
    TeslaBluetoothChargeSensorEntityDescription(
        key="charge_state_charging_state",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "charging",
            "complete",
            "disconnected",
            "stopped",
            "starting",
            "no_power",
        ],
        value_fn=lambda x: str(x.charging_state).lower() if x.charging_state else None,
    ),
)


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothClimateSensorEntityDescription(SensorEntityDescription):
    """Describes Tesla Bluetooth climate sensor entity."""

    value_fn: Callable[[ClimateState], Any] = lambda _: None


CLIMATE_DESCRIPTIONS: tuple[TeslaBluetoothClimateSensorEntityDescription, ...] = (
    TeslaBluetoothClimateSensorEntityDescription(
        key="climate_state_inside_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.inside_temp_celsius,
    ),
    TeslaBluetoothClimateSensorEntityDescription(
        key="climate_state_outside_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.outside_temp_celsius,
    ),
    TeslaBluetoothClimateSensorEntityDescription(
        key="climate_state_driver_temp_setting",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.driver_temp_setting,
    ),
    TeslaBluetoothClimateSensorEntityDescription(
        key="climate_state_passenger_temp_setting",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.passenger_temp_setting,
    ),
)


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothDriveSensorEntityDescription(SensorEntityDescription):
    """Describes Tesla Bluetooth drive sensor entity."""

    value_fn: Callable[[DriveState], Any] = lambda _: None


DRIVE_DESCRIPTIONS: tuple[TeslaBluetoothDriveSensorEntityDescription, ...] = (
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        value_fn=lambda x: x.odometer_in_hundredths_of_a_mile * 100,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda x: x.speed,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.power,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_shift_state",
        device_class=SensorDeviceClass.ENUM,
        options=["p", "r", "n", "d"],
        value_fn=lambda x: str(x.shift_state).lower() if x.shift_state else None,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_active_route_destination",
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.active_route_destination,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_active_route_energy_at_arrival",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.active_route_energy_at_arrival,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_active_route_miles_to_arrival",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.MILES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.active_route_miles_to_arrival,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_active_route_minutes_to_arrival",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.active_route_minutes_to_arrival,
    ),
    TeslaBluetoothDriveSensorEntityDescription(
        key="drive_state_active_route_traffic_minutes_delay",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.active_route_traffic_minutes_delay,
    ),
)


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothTirePressureSensorEntityDescription(SensorEntityDescription):
    """Describes Tesla Bluetooth tire pressure sensor entity."""

    value_fn: Callable[[TirePressureState], Any] = lambda _: None


TIRE_PRESSURE_DESCRIPTIONS = (
    TeslaBluetoothTirePressureSensorEntityDescription(
        key="vehicle_state_tpms_pressure_fl",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.tpms_pressure_fl,
    ),
    TeslaBluetoothTirePressureSensorEntityDescription(
        key="vehicle_state_tpms_pressure_fr",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.tpms_pressure_fr,
    ),
    TeslaBluetoothTirePressureSensorEntityDescription(
        key="vehicle_state_tpms_pressure_rl",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.tpms_pressure_rl,
    ),
    TeslaBluetoothTirePressureSensorEntityDescription(
        key="vehicle_state_tpms_pressure_rr",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda x: x.tpms_pressure_rr,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeslaBluetoothConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tesla Bluetooth sensor platform from a config entry."""

    async_add_entities(
        chain(
            (
                TeslaBluetoothChargeSensorEntity(entry.runtime_data, description)
                for description in CHARGE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothClimateSensorEntity(entry.runtime_data, description)
                for description in CLIMATE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothDriveSensorEntity(entry.runtime_data, description)
                for description in DRIVE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothTirePressureSensorEntity(entry.runtime_data, description)
                for description in TIRE_PRESSURE_DESCRIPTIONS
            ),
        )
    )


class TeslaBluetoothSensorBase(TeslaBluetoothEntity, SensorEntity):
    """Base class for Tesla Bluetooth sensors."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        data: TeslaBluetoothData,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        super().__init__(data, description.key)

    def _async_update_attrs(self) -> None:
        """Update the attributes of the sensor."""
        try:
            self._attr_native_value = self.entity_description.value_fn(
                self.coordinator.data
            )
        except (AttributeError, TypeError):
            self._attr_native_value = None


class TeslaBluetoothChargeSensorEntity(
    TeslaBluetoothSensorBase, TeslaBluetoothChargeEntity
):
    """Sensor for Tesla Bluetooth charge state."""

    entity_description: TeslaBluetoothChargeSensorEntityDescription


class TeslaBluetoothClimateSensorEntity(
    TeslaBluetoothSensorBase, TeslaBluetoothClimateEntity
):
    """Sensor for Tesla Bluetooth climate state."""

    entity_description: TeslaBluetoothClimateSensorEntityDescription


class TeslaBluetoothDriveSensorEntity(
    TeslaBluetoothSensorBase, TeslaBluetoothDriveEntity
):
    """Sensor for Tesla Bluetooth drive state."""

    entity_description: TeslaBluetoothDriveSensorEntityDescription


class TeslaBluetoothTirePressureSensorEntity(
    TeslaBluetoothSensorBase, TeslaBluetoothTirePressureEntity
):
    """Sensor for Tesla Bluetooth tire pressure state."""

    entity_description: TeslaBluetoothTirePressureSensorEntityDescription
