"""Binary Sensor platform for Tesla Bluetooth integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import chain

from tesla_fleet_api.tesla.vehicle.bluetooth import (
    ChargeState,
    ClimateState,
    TirePressureState,
    VehicleStatus,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TeslaBluetoothConfigEntry
from .entity import (
    TeslaBluetoothChargeEntity,
    TeslaBluetoothClimateEntity,
    TeslaBluetoothEntity,
    TeslaBluetoothStateEntity,
    TeslaBluetoothTirePressureEntity,
)
from .models import TeslaBluetoothData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothStateBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Tesla Bluetooth state binary sensor entity."""

    value_fn: Callable[[VehicleStatus], bool] = bool


STATE_DESCRIPTIONS: tuple[TeslaBluetoothStateBinarySensorEntityDescription, ...] = (
    TeslaBluetoothStateBinarySensorEntityDescription(
        key="state",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda x: x.vehicleSleepStatus == 1,
    ),
    TeslaBluetoothStateBinarySensorEntityDescription(
        key="vehicle_state_is_user_present",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda x: x.userPresence == 2,
    ),
    TeslaBluetoothStateBinarySensorEntityDescription(
        key="vehicle_state_df",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.closureStatuses.frontDriverDoor in [1, 2],
    ),
    TeslaBluetoothStateBinarySensorEntityDescription(
        key="vehicle_state_dr",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.closureStatuses.rearDriverDoor in [1, 2],
    ),
    TeslaBluetoothStateBinarySensorEntityDescription(
        key="vehicle_state_pf",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.closureStatuses.frontPassengerDoor in [1, 2],
    ),
    TeslaBluetoothStateBinarySensorEntityDescription(
        key="vehicle_state_pr",
        device_class=BinarySensorDeviceClass.DOOR,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.closureStatuses.rearPassengerDoor in [1, 2],
    ),
)


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothChargeBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Tesla Bluetooth state binary sensor entity."""

    value_fn: Callable[[ChargeState], bool] = bool


CHARGE_DESCRIPTIONS: tuple[TeslaBluetoothChargeBinarySensorEntityDescription, ...] = (
    TeslaBluetoothChargeBinarySensorEntityDescription(
        key="charge_state_charger_phases",
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.charger_phases > 1,
    ),
    TeslaBluetoothChargeBinarySensorEntityDescription(
        key="charge_state_preconditioning_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.preconditioning_enabled,
    ),
    TeslaBluetoothChargeBinarySensorEntityDescription(
        key="charge_state_scheduled_charging_pending",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.scheduled_charging_pending,
    ),
    TeslaBluetoothChargeBinarySensorEntityDescription(
        key="charge_state_trip_charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.trip_charging,
    ),
    TeslaBluetoothChargeBinarySensorEntityDescription(
        key="charge_state_conn_charge_cable",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda x: bool(x.conn_charge_cable),
    ),
)


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothClimateBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Tesla Bluetooth state binary sensor entity."""

    value_fn: Callable[[ClimateState], bool] = bool


CLIMATE_DESCRIPTIONS: tuple[TeslaBluetoothClimateBinarySensorEntityDescription, ...] = (
    TeslaBluetoothClimateBinarySensorEntityDescription(
        key="climate_state_is_preconditioning",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.is_preconditioning,
    ),
    TeslaBluetoothClimateBinarySensorEntityDescription(
        key="climate_state_cabin_overheat_protection_actively_cooling",
        device_class=BinarySensorDeviceClass.HEAT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothTirePressureBinarySensorEntityDescription(
    BinarySensorEntityDescription
):
    """Describes Tesla Bluetooth state binary sensor entity."""

    value_fn: Callable[[TirePressureState], bool] = bool


TIRE_PRESSURE_DESCRIPTIONS = (
    # TeslaBluetoothVehicleStateBinarySensorEntityDescription(
    #    key="vehicle_state_dashcam_state",
    #    device_class=BinarySensorDeviceClass.RUNNING,
    #    entity_category=EntityCategory.DIAGNOSTIC,
    #    entity_registry_enabled_default=False,
    #    value_fn=lambda x: x.sentr == "Recording",
    # ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_soft_warning_fl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_soft_warning_fl,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_soft_warning_fr",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_soft_warning_fr,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_soft_warning_rl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_soft_warning_rl,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_soft_warning_rr",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_soft_warning_rr,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_hard_warning_fl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_hard_warning_fl,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_hard_warning_fr",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_hard_warning_fr,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_hard_warning_rl",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_hard_warning_rl,
    ),
    TeslaBluetoothTirePressureBinarySensorEntityDescription(
        key="vehicle_state_tpms_hard_warning_rr",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: x.tpms_hard_warning_rr,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeslaBluetoothConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tesla Fleet binary sensor platform from a config entry."""

    async_add_entities(
        chain(
            (
                TeslaBluetoothStateBinarySensorEntity(entry.runtime_data, description)
                for description in STATE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothChargeBinarySensorEntity(entry.runtime_data, description)
                for description in CHARGE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothClimateBinarySensorEntity(entry.runtime_data, description)
                for description in CLIMATE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothTirePressureBinarySensorEntity(
                    entry.runtime_data, description
                )
                for description in TIRE_PRESSURE_DESCRIPTIONS
            ),
        )
    )


class TeslaBluetoothBinarySensorBase(TeslaBluetoothEntity, BinarySensorEntity):
    """Base class for Tesla Bluetooth binary sensors."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        data: TeslaBluetoothData,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        self.entity_description = description
        super().__init__(data, description.key)

    def _async_update_attrs(self) -> None:
        """Update the attributes of the binary sensor."""
        self._attr_is_on = self.entity_description.value_fn(self.coordinator.data)


class TeslaBluetoothStateBinarySensorEntity(
    TeslaBluetoothBinarySensorBase, TeslaBluetoothStateEntity
):
    """Binary sensor for Tesla Bluetooth vehicle status."""

    entity_description: TeslaBluetoothStateBinarySensorEntityDescription


class TeslaBluetoothChargeBinarySensorEntity(
    TeslaBluetoothBinarySensorBase, TeslaBluetoothChargeEntity
):
    """Binary sensor for Tesla Bluetooth charge state."""

    entity_description: TeslaBluetoothChargeBinarySensorEntityDescription


class TeslaBluetoothClimateBinarySensorEntity(
    TeslaBluetoothBinarySensorBase, TeslaBluetoothClimateEntity
):
    """Binary sensor for Tesla Bluetooth climate state."""

    entity_description: TeslaBluetoothClimateBinarySensorEntityDescription


class TeslaBluetoothTirePressureBinarySensorEntity(
    TeslaBluetoothBinarySensorBase, TeslaBluetoothTirePressureEntity
):
    """Binary sensor for Tesla Bluetooth tire pressure state."""

    entity_description: TeslaBluetoothTirePressureBinarySensorEntityDescription
