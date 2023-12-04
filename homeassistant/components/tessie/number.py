"""Number platform for Tessie integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tessie_api import set_charge_limit, set_charging_amps, set_speed_limit

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieCategory
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


@dataclass
class TessieNumberEntityDescription(NumberEntityDescription):
    """Class describing Tessie number entities."""

    func_min_value: Callable | None = None
    func_max_value: Callable | None = None
    func_value: Callable | None = None
    update_func: Callable | None = None
    update_param: str | None = None


DESCRIPTIONS: dict[TessieCategory, tuple[TessieNumberEntityDescription, ...]] = {
    TessieCategory.CHARGE_STATE: (
        TessieNumberEntityDescription(
            key="charge_current_request",
            translation_key="charge_current",
            native_min_value=0,
            func_max_value=lambda x: x["charge_current_request_max"],
            update_func=set_charging_amps,
            update_param="amps",
            native_step=1,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=NumberDeviceClass.CURRENT,
        ),
        TessieNumberEntityDescription(
            key="charge_limit_soc",
            translation_key="charge_limit_soc",
            func_min_value=lambda x: x["charge_limit_soc_min"],
            func_max_value=lambda x: x["charge_limit_soc_max"],
            update_func=set_charge_limit,
            update_param="percent",
            native_step=1,
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.BATTERY,
        ),
    ),
    TessieCategory.VEHICLE_STATE: (
        TessieNumberEntityDescription(
            key="speed_limit_mode",
            translation_key="speed_limit_mode",
            func_value=lambda x: x["speed_limit_mode"]["current_limit_mph"],
            func_min_value=lambda x: x["speed_limit_mode"]["max_limit_mph"],
            func_max_value=lambda x: x["speed_limit_mode"]["min_limit_mph"],
            update_func=set_speed_limit,
            update_param="mph",
            native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
            device_class=NumberDeviceClass.SPEED,
            mode=NumberMode.BOX,
            native_step=1,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            TessieNumberEntity(coordinator, vin, category, description)
            for vin, vehicle in coordinator.data.items()
            for category, descriptions in DESCRIPTIONS.items()
            if category in vehicle
            for description in descriptions
            if description.key in vehicle[category]
        ]
    )


class TessieNumberEntity(TessieEntity, NumberEntity):
    """Base class for Tessie number entity."""

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
        category: str,
        description: TessieNumberEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, vin, category, description.key)
        self.entity_description: TessieNumberEntityDescription = description

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.entity_description.func_value:
            return self.entity_description.func_value(self.parent())
        return self.get()

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        if self.entity_description.func_min_value:
            return self.entity_description.func_min_value(self.parent())
        return super().native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        if self.entity_description.func_max_value:
            return self.entity_description.func_max_value(self.parent())
        return super().native_max_value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        assert self.entity_description.update_func
        assert self.entity_description.update_param

        await self.run(
            self.entity_description.update_func,
            **{self.entity_description.update_param: value},
        )


class TessieCurrentChargeNumberEntity(TessieEntity, NumberEntity):
    """Number entity for current charge."""

    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_ative_unit_of_measurement = (UnitOfElectricCurrent.AMPERE,)
    _attr_device_class = NumberDeviceClass.CURRENT

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, vin, TessieCategory.CHARGE_STATE, "charge_current_request"
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the number."""
        self.get()

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        self.get("charge_current_request_max")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        assert self.entity_description.update_func
        assert self.entity_description.update_param

        await self.run(
            self.entity_description.update_func,
            **{self.entity_description.update_param: value},
        )
