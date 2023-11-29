"""Device Tracker platform for Tessie integration."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, TessieApi
from .entity import TessieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie device tracker platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator

    async_add_entities(
        [
            EntityClass(coordinator, vin)
            for EntityClass in (
                TessieDeviceTrackerLocationEntity,
                TessieDeviceTrackerRouteEntity,
            )
            for vin in coordinator.data
        ]
    )


class TessieDeviceTrackerLocationEntity(TessieEntity, TrackerEntity):
    """Vehicle Location Device Tracker Class."""

    _attr_name = "Location"

    def __init__(
        self,
        coordinator,
        vin: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, vin, TessieApi.DRIVE_STATE, "location")

    @property
    def source_type(self) -> SourceType | str:
        """Return the source type of the device tracker."""
        return SourceType.GPS

    @property
    def longitude(self) -> float | None:
        """Return the state of the device tracker."""
        return self.get_other("longitude")

    @property
    def latitude(self) -> float | None:
        """Return the state of the device tracker."""
        return self.get_other("latitude")

    @property
    def extra_state_attributes(self) -> dict[str, StateType] | None:
        """Return device state attributes."""
        return {
            "heading": self.get_other("heading"),
            "speed": self.get_other("speed"),
        }


class TessieDeviceTrackerRouteEntity(TessieEntity, TrackerEntity):
    """Vehicle Navigation Device Tracker Class."""

    _attr_name = "Route"

    def __init__(
        self,
        coordinator,
        vin: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, vin, TessieApi.DRIVE_STATE, "route")

    @property
    def source_type(self) -> SourceType | str:
        """Return the source type of the device tracker."""
        return SourceType.GPS

    @property
    def longitude(self) -> float | None:
        """Return the state of the device tracker."""
        return self.get_other("active_route_longitude")

    @property
    def latitude(self) -> float | None:
        """Return the state of the device tracker."""
        return self.get_other("active_route_latitude")
