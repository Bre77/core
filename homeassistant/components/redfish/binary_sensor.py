"""Binary Sensor platform for Redfish integration."""

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    BinarySensorEntity,
)

from .const import DOMAIN as REDFISH_DOMAIN, REDFISH_STATE_ON
from .entity import RedfishEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Redfish motion platform."""

    instance = hass.data[REDFISH_DOMAIN][config_entry.entry_id]

    entities = []
    for id in instance["coordinator"].data:
        entities.append(RedfishIndicatorLED(instance, id))
    async_add_entities(entities)


class RedfishIndicatorLED(RedfishEntity, BinarySensorEntity):
    """Redfish Filter."""

    @property
    def name(self):
        """Return the name."""
        return f"{self._name} Indicator LED"

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._uid}-led"

    @property
    def device_class(self):
        """Return the device class of the vent."""
        return DEVICE_CLASS_PROBLEM

    @property
    def is_on(self):
        """Return if light is on."""
        return self._data["IndicatorLED"] == REDFISH_STATE_ON
