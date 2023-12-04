"""Binary Sensor platform for Tessie integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TessieCategory
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


@dataclass
class TessieBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes Tessie binary sensor entity."""

    is_on: Callable[..., bool] = lambda x: x


DESCRIPTIONS: dict[TessieCategory, tuple[TessieBinarySensorEntityDescription, ...]] = {
    TessieCategory.CHARGE_STATE: (
        TessieBinarySensorEntityDescription(
            key="battery_heater_on",
            translation_key="battery_heater_on",
            device_class=BinarySensorDeviceClass.HEAT,
        ),
        TessieBinarySensorEntityDescription(
            key="charge_enable_request",
            translation_key="charge_enable_request",
            device_class=BinarySensorDeviceClass.POWER,
        ),
        TessieBinarySensorEntityDescription(
            key="charge_port_door_open",
            translation_key="charge_port_door_open",
            device_class=BinarySensorDeviceClass.OPENING,
        ),
        TessieBinarySensorEntityDescription(
            key="charging_state",
            translation_key="charging_state",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            is_on=lambda x: x == "Charging",
        ),
        TessieBinarySensorEntityDescription(
            key="preconditioning_enabled",
            translation_key="preconditioning_enabled",
        ),
        TessieBinarySensorEntityDescription(
            key="scheduled_charging_pending",
            translation_key="scheduled_charging_pending",
        ),
        TessieBinarySensorEntityDescription(
            key="trip_charging", translation_key="trip_charging"
        ),
    ),
    TessieCategory.CLIMATE_STATE: (
        TessieBinarySensorEntityDescription(
            key="auto_seat_climate_left",
            translation_key="auto_seat_climate_left",
            device_class=BinarySensorDeviceClass.HEAT,
        ),
        TessieBinarySensorEntityDescription(
            key="auto_seat_climate_right",
            translation_key="auto_seat_climate_right",
            device_class=BinarySensorDeviceClass.HEAT,
        ),
        TessieBinarySensorEntityDescription(
            key="auto_steering_wheel_heat",
            translation_key="auto_steering_wheel_heat",
            device_class=BinarySensorDeviceClass.HEAT,
        ),
        TessieBinarySensorEntityDescription(
            key="cabin_overheat_protection",
            translation_key="cabin_overheat_protection",
            device_class=BinarySensorDeviceClass.RUNNING,
            is_on=lambda x: x == "On",
        ),
        TessieBinarySensorEntityDescription(
            key="cabin_overheat_protection_actively_cooling",
            translation_key="cabin_overheat_protection_actively_cooling",
            device_class=BinarySensorDeviceClass.HEAT,
        ),
    ),
    TessieCategory.VEHICLE_STATE: (
        TessieBinarySensorEntityDescription(
            key="dashcam_state",
            translation_key="dashcam_state",
            device_class=BinarySensorDeviceClass.RUNNING,
            is_on=lambda x: x == "Recording",
        ),
        TessieBinarySensorEntityDescription(
            key="is_user_present",
            translation_key="is_user_present",
            device_class=BinarySensorDeviceClass.PRESENCE,
        ),
        TessieBinarySensorEntityDescription(
            key="tpms_soft_warning_fl",
            translation_key="tpms_soft_warning_fl",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        TessieBinarySensorEntityDescription(
            key="tpms_soft_warning_fr",
            translation_key="tpms_soft_warning_fr",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        TessieBinarySensorEntityDescription(
            key="tpms_soft_warning_rl",
            translation_key="tpms_soft_warning_rl",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        TessieBinarySensorEntityDescription(
            key="tpms_soft_warning_rr",
            translation_key="tpms_soft_warning_rr",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie binary sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            TessieBinarySensorEntity(coordinator, vin, category, description)
            for vin, vehicle in coordinator.data.items()
            for category, descriptions in DESCRIPTIONS.items()
            if category in vehicle
            for description in descriptions
            if description.key in vehicle[category]
        ]
    )


class TessieBinarySensorEntity(TessieEntity, BinarySensorEntity):
    """Base class for Tessie binary sensors."""

    entity_description: TessieBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
        category: str,
        description: TessieBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, vin, category, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        return self.entity_description.is_on(self.get())
