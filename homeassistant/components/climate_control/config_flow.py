"""Config Flow for Climate Control integration."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_COUNT

# from homeassistant.const import
# from homeassistant.components.cover import DOMAIN as COVER
# from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    CONF_ZONES,
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
            self.count = user_input[CONF_COUNT]
            self.zones = []

            # Abort if already configured
            await self.async_set_unique_id(self.climate_entity)
            self._abort_if_unique_id_configured()

            return await self.async_step_zone()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIMATE_ENTITY): str,
                    vol.Required(CONF_COUNT): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_zone(self, user_input=None):
        """Get zone configuration from the user."""
        errors = {}
        if user_input is not None:
            self.zones.append(user_input)
            if len(self.zones) < self.count:
                return await self.async_step_zone()
            return self.async_create_entry(
                title=self.climate_entity,
                data={
                    CONF_CLIMATE_ENTITY: self.climate_entity,
                    CONF_ZONES: self.zones,
                },
            )
        return self.async_show_form(
            step_id="zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COVER_ENTITY): str,
                    vol.Required(CONF_SENSOR_ENTITY): str,
                }
            ),
            errors=errors,
        )
