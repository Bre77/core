"""Switch platform for Tessie integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tessie_api import (
    disable_sentry_mode,
    disable_valet_mode,
    enable_sentry_mode,
    enable_valet_mode,
    start_charging,
    start_defrost,
    stop_charging,
    stop_defrost,
)

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieCategory
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


@dataclass
class TessieSwitchEntityDescription(SwitchEntityDescription):
    """Describes Tessie Switch entity."""

    on_func: Callable = lambda x: None
    off_func: Callable = lambda x: None
    device_class: SwitchDeviceClass = SwitchDeviceClass.SWITCH


DESCRIPTIONS: dict[TessieCategory, tuple[TessieSwitchEntityDescription, ...]] = {
    TessieCategory.CHARGE_STATE: (
        TessieSwitchEntityDescription(
            key="charge_enable_request",
            on_func=start_charging,
            off_func=stop_charging,
        ),
    ),
    TessieCategory.CLIMATE_STATE: (
        TessieSwitchEntityDescription(
            key="defrost_mode",
            on_func=start_defrost,
            off_func=stop_defrost,
        ),
    ),
    TessieCategory.VEHICLE_STATE: (
        TessieSwitchEntityDescription(
            key="sentry_mode",
            on_func=enable_sentry_mode,
            off_func=disable_sentry_mode,
        ),
        TessieSwitchEntityDescription(
            key="valet_mode",
            on_func=enable_valet_mode,
            off_func=disable_valet_mode,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie Switch platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            TessieSwitchEntity(coordinator, vin, category, description)
            for vin, vehicle in coordinator.data.items()
            for category, descriptions in DESCRIPTIONS.items()
            if category in vehicle
            for description in descriptions
            if description.key in vehicle[category]
        ]
    )


class TessieSwitchEntity(TessieEntity, SwitchEntity):
    """Base class for Tessie Switch."""

    entity_description: TessieSwitchEntityDescription

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
        category: str,
        description: TessieSwitchEntityDescription,
    ) -> None:
        """Initialize the Switch."""
        super().__init__(coordinator, vin, category, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return the state of the Switch."""
        return self.get()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the Switch."""
        await self.run(self.entity_description.on_func)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the Switch."""
        await self.run(self.entity_description.off_func)
