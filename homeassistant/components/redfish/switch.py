"""Switch platform for Redfish integration."""

from homeassistant.helpers.entity import ToggleEntity

from .const import DOMAIN as REDFISH_DOMAIN, REDFISH_POWER_ON
from .entity import RedfishEntity

# REDFISH_RESETTYPE_ON = "On"
# REDFISH_RESETTYPE_OFF = "On"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Redfish toggle platform."""

    instance = hass.data[REDFISH_DOMAIN][config_entry.entry_id]

    entities = []
    for id in instance["coordinator"].data:
        entities.append(RedfishPower(instance, id))
    async_add_entities(entities)


class RedfishPower(RedfishEntity, ToggleEntity):
    """Representation of Redfish fresh air control."""

    @property
    def name(self):
        """Return the name."""
        return f"{self._name} Power"

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._uid}-power"

    @property
    def is_on(self):
        """Return the power state."""
        return self._data["Systems"]["PowerState"] == REDFISH_POWER_ON

    @property
    def icon(self):
        """Return a representative icon of the power switch."""
        return ["mdi:server-network-off", "mdi:server-network"][self.is_on]

    async def async_turn_on(self, **kwargs):
        """Turn power on."""
        if not self.is_on:
            await self.async_change(
                self._data["Systems"]["Actions"]["#ComputerSystem.Reset"]["target"],
                {"ResetType": "PushPowerButton"},
            )

    async def async_turn_off(self, **kwargs):
        """Turn power off."""
        if self.is_on:
            await self.async_change(
                self._data["Systems"]["Actions"]["#ComputerSystem.Reset"]["target"],
                {"ResetType": "PushPowerButton"},
            )
