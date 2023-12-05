"""Climate platform for Tessie integration."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from tessie_api.climate import (
    set_climate_keeper_mode,
    set_temperature,
    start_climate_preconditioning,
    stop_climate,
)

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieCategory
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0

KEEPER_MODES = OrderedDict(
    [("off", "Normal"), ("on", "Keep"), ("dog", "Dog"), ("camp", "Camp")]
)

KEEPER_NAMES = list(KEEPER_MODES.values())
KEEPER_NAME_TO_VALUE = {v: k for k, v in KEEPER_MODES.items()}
KEEPER_NAME_TO_INDEX = {v: i for i, (k, v) in enumerate(KEEPER_MODES.items())}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie Climate platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [TessieClimateEntity(coordinator, vin) for vin in coordinator.data]
    )


class TessieClimateEntity(TessieEntity, ClimateEntity):
    """Vehicle Location Climate Class."""

    _attr_precision = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes: list = KEEPER_NAMES

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
    ) -> None:
        """Initialize the Climate entity."""
        super().__init__(
            coordinator, vin, TessieCategory.CLIMATE_STATE, "is_climate_on"
        )

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        if self.get():
            return HVACMode.HEAT_COOL
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.get("inside_temp")

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self.get("driver_temp_setting")

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self.get("max_avail_temp")

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self.get("min_avail_temp")

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return KEEPER_MODES.get(self.get("climate_keeper_mode"))

    async def async_turn_on(self) -> None:
        """Set the climate state to on."""
        if await self.run(start_climate_preconditioning):
            self.set(("is_climate_on", True))

    async def async_turn_off(self) -> None:
        """Set the climate state to off."""
        if await self.run(stop_climate):
            self.set(("is_climate_on", False), ("climate_keeper_mode", "off"))

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the climate temperature."""
        temp = kwargs[ATTR_TEMPERATURE]
        if await self.run(set_temperature, temperature=temp):
            self.set(("driver_temp_setting", temp))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the climate mode and state."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the climate preset mode."""
        if await self.run(
            set_climate_keeper_mode, mode=KEEPER_NAME_TO_INDEX[preset_mode]
        ):
            self.set(
                ("climate_keeper_mode", KEEPER_NAME_TO_VALUE[preset_mode]),
                ("is_climate_on", preset_mode != "Normal"),
            )
