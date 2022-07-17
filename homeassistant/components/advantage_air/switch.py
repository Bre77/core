"""Switch platform for Advantage Air integration."""
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ADVANTAGE_AIR_AIRCONS,
    ADVANTAGE_AIR_COORDINATOR,
    ADVANTAGE_AIR_STATE_OFF,
    ADVANTAGE_AIR_STATE_ON,
    ADVANTAGE_AIR_THINGS,
    DOMAIN as ADVANTAGE_AIR_DOMAIN,
)
from .entity import AdvantageAirAirconEntity, AdvantageAirThing


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AdvantageAir switch platform."""

    instance = hass.data[ADVANTAGE_AIR_DOMAIN][config_entry.entry_id]

    entities: list[SwitchEntity] = []
    if ADVANTAGE_AIR_AIRCONS in instance[ADVANTAGE_AIR_COORDINATOR].data:
        for ac_key, ac_device in (
            instance[ADVANTAGE_AIR_COORDINATOR].data[ADVANTAGE_AIR_AIRCONS].items()
        ):
            if ac_device["info"]["freshAirStatus"] != "none":
                entities.append(AdvantageAirFreshAir(instance, ac_key))

    if ADVANTAGE_AIR_THINGS in instance[ADVANTAGE_AIR_COORDINATOR].data:
        for thing in (
            instance[ADVANTAGE_AIR_COORDINATOR]
            .data[ADVANTAGE_AIR_THINGS]["things"]
            .values()
        ):
            if thing["channelDipState"] == 8:
                entities.append(AdvantageAirRelay(instance, thing))
    async_add_entities(entities)


class AdvantageAirFreshAir(AdvantageAirAirconEntity, SwitchEntity):
    """Representation of Advantage Air fresh air control."""

    _attr_icon = "mdi:air-filter"

    def __init__(self, instance, ac_key):
        """Initialize an Advantage Air fresh air control."""
        super().__init__(instance, ac_key)
        self._attr_name = f'{self._ac["name"]} Fresh Air'
        self._attr_unique_id = (
            f'{self.coordinator.data["system"]["rid"]}-{ac_key}-freshair'
        )

    @property
    def is_on(self):
        """Return the fresh air status."""
        return self._ac["freshAirStatus"] == ADVANTAGE_AIR_STATE_ON

    async def async_turn_on(self, **kwargs):
        """Turn fresh air on."""
        await self.async_set_aircon(
            {self.ac_key: {"info": {"freshAirStatus": ADVANTAGE_AIR_STATE_ON}}}
        )

    async def async_turn_off(self, **kwargs):
        """Turn fresh air off."""
        await self.async_set_aircon(
            {self.ac_key: {"info": {"freshAirStatus": ADVANTAGE_AIR_STATE_OFF}}}
        )


class AdvantageAirRelay(AdvantageAirThing, SwitchEntity):
    """Representation of Advantage Air Thing."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the thing on."""
        await self.async_set_thing({"id": self._id, "state": ADVANTAGE_AIR_STATE_ON})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the thing off."""
        await self.async_set_thing({"id": self._id, "state": ADVANTAGE_AIR_STATE_OFF})
