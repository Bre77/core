"""Config Flow for Climate Control integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_COUNT

# from homeassistant.const import
# from homeassistant.components.cover import DOMAIN as COVER
# from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    CONF_AREAS,
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    DOMAIN,
)


class ClimateControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Climate Control."""

    VERSION = 1

    DOMAIN = DOMAIN

    async def async_step_user(self, user_input=None):
        """Get configuration from the user."""
        errors = {}
        if user_input is not None:

            self.climate_entity = user_input[CONF_CLIMATE_ENTITY]
            self.areas = user_input[CONF_AREAS]
            self.zones = []

            # Abort if already configured
            await self.async_set_unique_id(self.climate_entity)
            self._abort_if_unique_id_configured()

            return await self.async_step_zone()

        climate_entities = self.hass.states.async_entity_ids("climate")

        areas = {}
        area_registry = async_get_area_registry(self.hass)
        for entry in area_registry.async_list_areas():
            areas[entry.id] = entry.name

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIMATE_ENTITY): cv.multi_select(
                        climate_entities
                    ),
                    vol.Required(CONF_AREAS): cv.multi_select(areas),
                }
            ),
            errors=errors,
        )

    async def async_step_zone(self, user_input=None):
        """Get zone configuration from the user."""
        errors = {}
        if user_input is not None:
            user_input["area"] = self.areas[len(self.zones)]
            self.zones.append(user_input)
            if len(self.zones) >= len(self.areas):
                # return await self.async_step_zone()
                return self.async_create_entry(
                    title=self.climate_entity,
                    data={
                        CONF_CLIMATE_ENTITY: self.climate_entity,
                        CONF_AREAS: self.zones,
                    },
                )
        entity_registry = async_get_entity_registry(self.hass)
        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COVER_ENTITY): cv.multi_select(
                        self.hass.states.async_entity_ids("cover")
                    ),
                    vol.Required(CONF_SENSOR_ENTITY): cv.multi_select(
                        entity_registry.async_get_device_class_lookup(
                            ("cover", "temperature")
                        )
                    ),
                }
            ),
            errors=errors,
        )
