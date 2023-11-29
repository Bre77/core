"""Climate platform for Tessie integration."""
from __future__ import annotations

from tessie_api import set_climate_keeper_mode

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieApi
from .entity import TessieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie Climate platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator
    api_key = entry.data[CONF_ACCESS_TOKEN]

    async_add_entities(
        [TessieClimateEntity(coordinator, vin, api_key) for vin in coordinator.data]
    )


class TessieClimateEntity(TessieEntity, ClimateEntity):
    """Vehicle Location Climate Class."""

    _attr_name = "Climate"
    _attr_precision = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes: list = ["Normal", "Keep", "Dog", "Camp"]

    def __init__(
        self,
        coordinator,
        vin: str,
        api_key: str,
    ) -> None:
        """Initialize the Climate entity."""
        super().__init__(coordinator, vin, TessieApi.CLIMATE_STATE, "is_climate_on")
        self.api_key = api_key

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
        return self._attr_preset_modes[self.get("climate_keeper_mode")]

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        return await set_climate_keeper_mode(
            session=async_get_clientsession(self.hass),
            vin=self.vin,
            api_key=self.api_key,
            mode=self._attr_preset_modes.index(preset_mode),
        )
