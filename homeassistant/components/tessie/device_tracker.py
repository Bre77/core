"""Device Tracker platform for Tessie integration."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, TessieGroup
from .coordinator import TessieDataUpdateCoordinator
from .entity import TessieEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tessie device tracker platform from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator
    api_key = entry.data[CONF_ACCESS_TOKEN]

    async_add_entities(
        [
            EntityClass(api_key, coordinator, vin)
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
        api_key: str,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
    ) -> None:
        """Initialize the device tracker."""
        super().__init__(api_key, coordinator, vin, TessieGroup.DRIVE_STATE, self.key)

    @property
    def source_type(self) -> SourceType | str:
        """Return the source type of the device tracker."""
        return SourceType.GPS


class TessieDeviceTrackerLocationEntity(TessieDeviceTrackerEntity):
    """Vehicle Location Device Tracker Class."""

    _attr_translation_key = "location"
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

    _attr_translation_key = "route"
    key = "route"

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the device tracker."""
        return self.get("active_route_longitude")

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the device tracker."""
        return self.get("active_route_latitude")
