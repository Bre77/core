"""Advantage Air parent entity class."""

from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ADVANTAGE_AIR_STATE_OFF, ADVANTAGE_AIR_STATE_ON, DOMAIN


class AdvantageAirEntity(CoordinatorEntity):
    """Parent class for Advantage Air Entities."""

    _attr_has_entity_name = True

    def __init__(self, instance):
        """Initialize common aspects of an Advantage Air entity."""
        super().__init__(instance["coordinator"])
        self._attr_unique_id = self.coordinator.data["system"]["rid"]


class AdvantageAirAcEntity(AdvantageAirEntity):
    """Parent class for Advantage Air AC Entities."""

    def __init__(self, instance, ac_key):
        """Initialize common aspects of an Advantage Air ac entity."""
        super().__init__(instance)
        self.async_change = instance["aircon"]
        self.ac_key = ac_key
        self._attr_unique_id += f"-{ac_key}"

        self._attr_device_info = DeviceInfo(
            via_device=(DOMAIN, self.coordinator.data["system"]["rid"]),
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="Advantage Air",
            model=self.coordinator.data["system"]["sysType"],
            name=self.coordinator.data["aircons"][self.ac_key]["info"]["name"],
        )

    @property
    def _ac(self):
        return self.coordinator.data["aircons"][self.ac_key]["info"]


class AdvantageAirZoneEntity(AdvantageAirAcEntity):
    """Parent class for Advantage Air Zone Entities."""

    def __init__(self, instance, ac_key, zone_key):
        """Initialize common aspects of an Advantage Air zone entity."""
        super().__init__(instance, ac_key)
        self.zone_key = zone_key
        self._attr_unique_id += f"-{zone_key}"

    @property
    def _zone(self):
        return self.coordinator.data["aircons"][self.ac_key]["zones"][self.zone_key]


class AdvantageAirThingEntity(AdvantageAirEntity):
    """Parent class for Advantage Air Things Entities."""

    def __init__(self, instance, thing, endpoint="things"):
        """Initialize common aspects of an Advantage Air Things entity."""
        super().__init__(instance)
        self.async_change = instance[endpoint]
        self._id = thing["id"]
        self._attr_unique_id += f"-{self._id}"

        self._attr_device_info = DeviceInfo(
            via_device=(DOMAIN, self.coordinator.data["system"]["rid"]),
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="Advantage Air",
            model="MyPlace",
            name=thing["name"],
        )

    @property
    def _thing(self):
        """Return the light object."""
        return self.coordinator.data["myThings"]["thing"][self._id]

    @property
    def is_on(self):
        """Return the fresh air status."""
        return self._thing["value"] > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self.async_change({"id": self._id, "state": ADVANTAGE_AIR_STATE_ON})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self.async_change({"id": self._id, "state": ADVANTAGE_AIR_STATE_OFF})
