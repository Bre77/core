"""Climate platform for Climate Control integration."""
from homeassistant.components.climate import ClimateEntity

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up ClimateControl climate platform."""

    instance = hass.data[ADVANTAGE_AIR_DOMAIN][config_entry.entry_id]

    entities = []
    for ac_key, ac_device in instance["coordinator"].data["aircons"].items():
        entities.append(ClimateControlAC(instance, ac_key))
        for zone_key, zone in ac_device["zones"].items():
            # Only add zone climate control when zone is in temperature control
            if zone["type"] != 0:
                entities.append(ClimateControlZone(instance, ac_key, zone_key))
    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        ADVANTAGE_AIR_SERVICE_SET_MYZONE,
        {},
        "set_myzone",
    )


class ClimateControlClimateEntity(ClimateControlEntity, ClimateEntity):