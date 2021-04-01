"""Sensor platform for Redfish integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import POWER_WATT

from .const import DOMAIN as REDFISH_DOMAIN
from .entity import RedfishEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Redfish sensor platform."""

    instance = hass.data[REDFISH_DOMAIN][config_entry.entry_id]

    entities = []
    for id in instance["coordinator"].data:
        entities.append(RedfishPowerConsumedWatts(instance, id))
        entities.append(RedfishPowerRequestedWatts(instance, id))
    async_add_entities(entities)


class RedfishPowerConsumedWatts(RedfishEntity, SensorEntity):
    """Representation of Redfish Zone Vent Sensor."""

    @property
    def name(self):
        """Return the name."""
        return f"{self._name} Power Consumed"

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._uid}-powerconsumed"

    @property
    def state(self):
        """Return the current value of the air vent."""
        return self._data["power"]["PowerConsumedWatts"]

    @property
    def unit_of_measurement(self):
        """Return the percent sign."""
        return POWER_WATT

    @property
    def icon(self):
        """Return a representative icon."""
        return "mdi:power-plug"


class RedfishPowerRequestedWatts(RedfishEntity, SensorEntity):
    """Representation of Redfish Zone Vent Sensor."""

    @property
    def name(self):
        """Return the name."""
        return f"{self._name} Power Requested"

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._uid}-powerequested"

    @property
    def state(self):
        """Return the current value of the air vent."""
        return self._data["power"]["PowerRequestedWatts"]

    @property
    def unit_of_measurement(self):
        """Return the percent sign."""
        return POWER_WATT

    @property
    def icon(self):
        """Return a representative icon."""
        return "mdi:power-plug"
