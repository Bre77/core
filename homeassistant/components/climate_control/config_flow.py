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
    CONF_AREA,
    CONF_AREAS,
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    CONF_ZONES,
    DOMAIN,
)

CONF_GUIDED = "guided"


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
            self.guided = user_input[CONF_GUIDED]
            print(self.climate_entity)
            print(self.areas)

            # Abort if already configured
            await self.async_set_unique_id(self.climate_entity)
            self._abort_if_unique_id_configured()

            return await self.async_step_zone()

        # Build Climate Entity List
        entity_registry = async_get_entity_registry(self.hass)
        climate_entities = {}
        for entity_id in self.hass.states.async_entity_ids("climate"):
            entity = entity_registry.async_get(entity_id)
            climate_entities[entity_id] = entity.name or entity.original_name

        # Build Area List
        areas = {}
        area_registry = async_get_area_registry(self.hass)
        for area in area_registry.async_list_areas():
            print(area)
            areas[area.id] = area.name

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIMATE_ENTITY): vol.In(climate_entities),
                    vol.Required(CONF_AREAS): cv.multi_select(areas),
                    vol.Optional(CONF_GUIDED, default=True): cv.boolean,
                }
            ),
            errors=errors,
        )

    async def async_step_zone(self, user_input=None):
        """Get zone configuration from the user."""
        errors = {}
        count = len(self.zones)
        if user_input is not None:
            user_input[CONF_AREA] = self.areas[count]
            self.zones.append(user_input)
            count += 1
            if count >= len(self.areas):
                # Create the config entry
                print(self.zones)
                return self.async_create_entry(
                    title=self.climate_entity,
                    data={
                        CONF_CLIMATE_ENTITY: self.climate_entity,
                        CONF_ZONES: self.zones,
                    },
                )

        area_id = self.areas[count]

        entity_registry = async_get_entity_registry(self.hass)
        # Build Damper Cover entity list
        cover_entities = {}
        for entity_id in self.hass.states.async_entity_ids("cover"):
            entity = entity_registry.async_get(entity_id)
            print(entity)
            if entity and (
                not self.guided
                or (entity.device_class == "damper" and entity.area_id == area_id)
            ):
                cover_entities[entity_id] = entity.name or entity.original_name

        # Build Temperature Sensor entity list
        sensor_entities = {}
        for entity_id in self.hass.states.async_entity_ids("sensor"):
            entity = entity_registry.async_get(entity_id)
            print(entity)
            if entity and (
                not self.guided
                or (entity.device_class == "temperature" and entity.area_id == area_id)
            ):
                print(
                    entity_id, "included", entity.area_id, area_id, entity.device_class
                )
                sensor_entities[entity_id] = entity.name or entity.original_name
            else:
                print(
                    entity_id, "excluded", entity.area_id, area_id, entity.device_class
                )

        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COVER_ENTITY): vol.In(cover_entities),
                    vol.Required(CONF_SENSOR_ENTITY): vol.In(sensor_entities),
                }
            ),
            last_step=(count + 1 == len(self.areas)),
            errors=errors,
        )
