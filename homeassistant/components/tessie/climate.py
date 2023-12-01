"""Climate platform for Tessie integration."""
from __future__ import annotations

from tessie_api import (
    set_climate_keeper_mode,
    start_climate_preconditioning,
    stop_climate,
)

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieGroup
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie Climate platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    api_key = entry.data[CONF_ACCESS_TOKEN]

    async_add_entities(
        [TessieClimateEntity(api_key, coordinator, vin) for vin in coordinator.data]
    )


class TessieClimateEntity(TessieEntity, ClimateEntity):
    """Vehicle Location Climate Class."""

    _attr_translation_key = "climate"
    _attr_precision = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes: list = ["Normal", "Keep", "Dog", "Camp"]

    def __init__(
        self,
        api_key: str,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
    ) -> None:
        """Initialize the Climate entity."""
        super().__init__(
            api_key, coordinator, vin, TessieGroup.CLIMATE_STATE, "is_climate_on"
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
        mode = self.get("climate_keeper_mode")
        if isinstance(mode, int):
            return self._attr_preset_modes[mode]
        return self._attr_preset_modes[0]

    async def async_turn_on(self) -> None:
        """Set the climate state to on."""
        await self.run(start_climate_preconditioning)

    async def async_turn_off(self) -> None:
        """Set the climate state to off."""
        await self.run(stop_climate)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the climate mode and state."""
        if hvac_mode == HVACMode.OFF:
            return await self.async_turn_off()
        return await self.async_turn_on()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the climate preset mode."""
        return await self.run(
            set_climate_keeper_mode, mode=self._attr_preset_modes.index(preset_mode)
        )
