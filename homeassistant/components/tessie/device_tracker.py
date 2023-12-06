"""Device Tracker platform for Tessie integration."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, TessieCategory
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie device tracker platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

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


class TessieDeviceTrackerEntity(TessieEntity, TrackerEntity):
    """Base class for Tessie Tracker Entities."""

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(coordinator, vin, TessieCategory.DRIVE_STATE, self.key)

    @property
    def source_type(self) -> SourceType | str:
        """Return the source type of the device tracker."""
        return SourceType.GPS


class TessieDeviceTrackerLocationEntity(TessieDeviceTrackerEntity):
    """Vehicle Location Device Tracker Class."""

    key = "location"

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the device tracker."""
        return self.get("longitude")

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the device tracker."""
        return self.get("latitude")

    @property
    def extra_state_attributes(self) -> dict[str, StateType] | None:
        """Return device state attributes."""
        return {
            "heading": self.get("heading"),
            "speed": self.get("speed"),
        }


class TessieDeviceTrackerRouteEntity(TessieDeviceTrackerEntity):
    """Vehicle Navigation Device Tracker Class."""

    key = "route"

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the device tracker."""
        return self.get("active_route_longitude")

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the device tracker."""
        return self.get("active_route_latitude")
