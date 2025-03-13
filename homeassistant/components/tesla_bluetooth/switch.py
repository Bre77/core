"""Switch platform for Tesla Fleet integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from itertools import chain
from typing import Any

from tesla_fleet_api.const import Seat
from tesla_fleet_api.tesla.vehicle.bluetooth import (
    ChargeState,
    ClimateState,
    VehicleBluetooth,
)

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TeslaBluetoothConfigEntry
from .entity import TeslaBluetoothChargeEntity, TeslaBluetoothClimateEntity
from .helpers import handle_vehicle_command
from .models import TeslaBluetoothData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothChargeSwitchEntityDescription(SwitchEntityDescription):
    """Describes Tesla Bluetooth Charge Switch entity."""

    on_func: Callable[[VehicleBluetooth], Awaitable[dict[str, Any]]]
    off_func: Callable[[VehicleBluetooth], Awaitable[dict[str, Any]]]
    value_func: Callable[[ChargeState], bool] = bool


@dataclass(frozen=True, kw_only=True)
class TeslaBluetoothClimateSwitchEntityDescription(SwitchEntityDescription):
    """Describes Tesla Bluetooth Climate Switch entity."""

    on_func: Callable[[VehicleBluetooth], Awaitable[dict[str, Any]]]
    off_func: Callable[[VehicleBluetooth], Awaitable[dict[str, Any]]]
    value_func: Callable[[ClimateState], bool] = bool


CLIMATE_DESCRIPTIONS: tuple[TeslaBluetoothClimateSwitchEntityDescription, ...] = (
    TeslaBluetoothClimateSwitchEntityDescription(
        key="climate_state_auto_seat_climate_left",
        on_func=lambda api: api.remote_auto_seat_climate_request(Seat.FRONT_LEFT, True),
        off_func=lambda api: api.remote_auto_seat_climate_request(
            Seat.FRONT_LEFT, False
        ),
        value_func=lambda state: state.auto_seat_climate_left,
    ),
    TeslaBluetoothClimateSwitchEntityDescription(
        key="climate_state_auto_seat_climate_right",
        on_func=lambda api: api.remote_auto_seat_climate_request(
            Seat.FRONT_RIGHT, True
        ),
        off_func=lambda api: api.remote_auto_seat_climate_request(
            Seat.FRONT_RIGHT, False
        ),
        value_func=lambda state: state.auto_seat_climate_right,
    ),
    # This one isn't in the Command Protocol
    # TeslaBluetoothClimateSwitchEntityDescription(
    #    key="climate_state_auto_steering_wheel_heat",
    #    on_func=lambda api: api.remote_auto_steering_wheel_heat_climate_request(
    #        on=True
    #    ),
    #    off_func=lambda api: api.remote_auto_steering_wheel_heat_climate_request(
    #        on=False
    #    ),
    #    value_func=lambda state: state.auto_steering_wheel_heat,
    # ),
    TeslaBluetoothClimateSwitchEntityDescription(
        key="climate_state_defrost_mode",
        on_func=lambda api: api.set_preconditioning_max(on=True, manual_override=False),
        off_func=lambda api: api.set_preconditioning_max(
            on=False, manual_override=False
        ),
        value_func=lambda state: not state.defrost_mode.HasField("Off"),
    ),
)
CHARGE_DESCRIPTIONS: tuple[TeslaBluetoothChargeSwitchEntityDescription, ...] = (
    TeslaBluetoothChargeSwitchEntityDescription(
        key="charge_state_charging_state",
        on_func=lambda api: api.charge_start(),
        off_func=lambda api: api.charge_stop(),
        value_func=lambda state: str(state.charging_state) in {"Starting", "Charging"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeslaBluetoothConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the TeslaBluetooth Switch platform from a config entry."""

    async_add_entities(
        chain(
            (
                TeslaBluetoothClimateSwitchEntity(entry.runtime_data, description)
                for description in CLIMATE_DESCRIPTIONS
            ),
            (
                TeslaBluetoothChargeSwitchEntity(entry.runtime_data, description)
                for description in CHARGE_DESCRIPTIONS
            ),
            (TeslaBluetoothPollingSwitchEntity(entry.runtime_data),),
        )
    )


class TeslaBluetoothClimateSwitchEntity(TeslaBluetoothClimateEntity, SwitchEntity):
    """Tesla Bluetooth climate switch entities."""

    entity_description: TeslaBluetoothClimateSwitchEntityDescription

    def __init__(
        self,
        data: TeslaBluetoothData,
        description: TeslaBluetoothClimateSwitchEntityDescription,
    ) -> None:
        """Initialize the Switch."""
        self.entity_description = description
        self._attr_device_class = SwitchDeviceClass.SWITCH
        super().__init__(data, description.key)

    def _async_update_attrs(self) -> None:
        """Update the attributes of the sensor."""

        self._attr_is_on = self.entity_description.value_func(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Switch."""
        await self.wake_up_if_asleep()
        await handle_vehicle_command(self.entity_description.on_func(self.vehicle))
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Switch."""
        await self.wake_up_if_asleep()
        await handle_vehicle_command(self.entity_description.off_func(self.vehicle))
        self._attr_is_on = False
        self.async_write_ha_state()


class TeslaBluetoothChargeSwitchEntity(TeslaBluetoothChargeEntity, SwitchEntity):
    """Tesla Bluetooth charge switch entities."""

    entity_description: TeslaBluetoothChargeSwitchEntityDescription

    def __init__(
        self,
        data: TeslaBluetoothData,
        description: TeslaBluetoothChargeSwitchEntityDescription,
    ) -> None:
        """Initialize the Switch."""
        self.entity_description = description
        self._attr_device_class = SwitchDeviceClass.SWITCH
        super().__init__(data, description.key)

    def _async_update_attrs(self) -> None:
        """Update the attributes of the sensor."""
        self._attr_is_on = self.entity_description.value_func(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Switch."""
        await self.wake_up_if_asleep()
        await handle_vehicle_command(self.entity_description.on_func(self.vehicle))
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Switch."""
        await self.wake_up_if_asleep()
        await handle_vehicle_command(self.entity_description.off_func(self.vehicle))
        self._attr_is_on = False
        self.async_write_ha_state()


class TeslaBluetoothPollingSwitchEntity(SwitchEntity, RestoreEntity):
    """Tesla Bluetooth polling switch entities."""

    def __init__(
        self,
        data: TeslaBluetoothData,
    ) -> None:
        """Initialize the Switch."""
        self.coordinators = data.coordinators
        self._attr_translation_key = "polling"
        self._attr_unique_id = f"{data.vehicle.vin}-polling"
        self._attr_device_class = SwitchDeviceClass.SWITCH

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self._attr_is_on = state.state == STATE_ON
        else:
            self._attr_is_on = True
        if not self._attr_is_on:
            self.coordinators.turn_off()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Switch."""
        self.coordinators.turn_on()
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Switch."""
        self.coordinators.turn_off()
        self._attr_is_on = False
        self.async_write_ha_state()
