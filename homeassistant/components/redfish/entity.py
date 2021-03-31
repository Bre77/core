"""Redfish parent entity class."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class RedfishEntity(CoordinatorEntity):
    """Parent class for Redfish Entities."""

    def __init__(self, instance, id):
        """Initialize common aspects of an Redfish sensor."""
        super().__init__(instance["coordinator"])
        self.async_change = instance["async_change"]
        self.id = id

    @property
    def _data(self):
        return self.coordinator.data[self.id]

    @property
    def _name(self):
        return self._data["HostName"] or self._data["Model"]

    @property
    def _uid(self):
        return self._data["UUID"]

    @property
    def device_info(self):
        """Return parent device information."""
        return {
            "identifiers": {(DOMAIN, self._uid)},
            "name": self._name,
            "manufacturer": self._data["Manufacturer"],
            "model": self._data["Model"],
            "sw_version": self._data["BiosVersion"],
        }
