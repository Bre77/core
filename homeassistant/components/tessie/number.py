"""Number platform for Tessie integration."""
from __future__ import annotations

from tessie_api import set_charge_limit, set_charging_amps, set_speed_limit

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie sensor platform from a config entry."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            EntityClass(coordinator)
            for EntityClass in (
                TessieChargeLimitSocNumberEntity,
                TessieSpeedLimitModeNumberEntity,
                TessieCurrentChargeNumberEntity,
            )
            for coordinator in coordinators
        ]
    )


class TessieCurrentChargeNumberEntity(TessieEntity, NumberEntity):
    """Number entity for current charge."""

    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charge_state-charge_current_request")

    @property
    def native_value(self) -> float:
        """Return the state of the number."""
        return self.get()

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self.get("charge_state-charge_current_request_max")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if await self.run(set_charging_amps, amps=value):
            self.set((self.key, value))


class TessieChargeLimitSocNumberEntity(TessieEntity, NumberEntity):
    """Number entity for charge limit soc."""

    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = NumberDeviceClass.BATTERY

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "charge_state-charge_limit_soc")

    @property
    def native_value(self) -> float:
        """Return the state of the number."""
        return self.get()

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self.get("charge_state-charge_limit_soc_min")

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self.get("charge_state-charge_limit_soc_max")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if await self.run(set_charge_limit, percent=value):
            self.set((self.key, value))


class TessieSpeedLimitModeNumberEntity(TessieEntity, NumberEntity):
    """Number entity for speed limit mode."""

    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfSpeed.MILES_PER_HOUR
    _attr_device_class = NumberDeviceClass.SPEED
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "vehicle_state-speed_limit_mode")

    @property
    def native_value(self) -> float:
        """Return the state of the number."""
        return self.get("vehicle_state-speed_limit_mode-current_limit_mph")

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self.get("vehicle_state-speed_limit_mode-min_limit_mph")

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self.get("vehicle_state-speed_limit_mode-max_limit_mph")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if await self.run(set_speed_limit, mph=value):
            self.set(("vehicle_state-speed_limit_mode-max_limit_mph", value))
