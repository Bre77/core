"""Number platform for Tesla Bluetooth integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from tesla_fleet_api.tesla.vehicle.bluetooth import ChargeState, VehicleBluetooth

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, PRECISION_WHOLE, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TeslaBluetoothConfigEntry
from .entity import TeslaBluetoothChargeEntity
from .helpers import handle_vehicle_command
from .models import TeslaBluetoothData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothChargeNumberEntityDescription(NumberEntityDescription):
    """Describes Tesla Bluetooth Charge Number entity."""

    func: Callable[[VehicleBluetooth, int], Awaitable[Any]]
    value_fn: Callable[[ChargeState], int]
    min_fn: Callable[[ChargeState], int]
    max_fn: Callable[[ChargeState], int]


CHARGE_DESCRIPTIONS: tuple[TeslaBluetoothChargeNumberEntityDescription, ...] = (
    TeslaBluetoothChargeNumberEntityDescription(
        key="charge_state_charge_current_request",
        native_step=PRECISION_WHOLE,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=NumberDeviceClass.CURRENT,
        mode=NumberMode.AUTO,
        value_fn=lambda state: state.charge_current_request,
        min_fn=lambda state: 0,
        max_fn=lambda state: state.charge_current_request_max,
        func=lambda ble, value: ble.set_charging_amps(value),
    ),
    TeslaBluetoothChargeNumberEntityDescription(
        key="charge_state_charge_limit_soc",
        native_step=PRECISION_WHOLE,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.AUTO,
        value_fn=lambda state: state.charge_limit_soc,
        min_fn=lambda state: state.charge_limit_soc_min,
        max_fn=lambda state: state.charge_limit_soc_max,
        func=lambda api, value: api.set_charge_limit(value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeslaBluetoothConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the TeslaFleet number platform from a config entry."""

    async_add_entities(
        TeslaBluetoothChargeNumberEntity(
            entry.runtime_data,
            description,
        )
        for description in CHARGE_DESCRIPTIONS
    )


class TeslaBluetoothChargeNumberEntity(TeslaBluetoothChargeEntity, NumberEntity):
    """Vehicle number entity base class."""

    entity_description: TeslaBluetoothChargeNumberEntityDescription

    def __init__(
        self,
        data: TeslaBluetoothData,
        description: TeslaBluetoothChargeNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        self.entity_description = description
        super().__init__(
            data,
            description.key,
        )

    def _async_update_attrs(self) -> None:
        """Update the attributes of the entity."""
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.data
        )
        self._attr_native_min_value = self.entity_description.min_fn(
            self.coordinator.data
        )
        self._attr_native_max_value = self.entity_description.max_fn(
            self.coordinator.data
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        value = int(value)
        await self.wake_up_if_asleep()
        await handle_vehicle_command(self.entity_description.func(self.vehicle, value))
        self._attr_native_value = value
        self.async_write_ha_state()
