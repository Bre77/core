"""Config Flow for Redfish integration."""
from aiohttp import BasicAuth, ClientTimeout
from aiohttp.web import HTTPError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

REDFISH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class RedfishConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Redfish API connection."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    DOMAIN = DOMAIN

    async def async_step_user(self, user_input=None):
        """Get configuration from the user."""
        errors = {}
        if user_input:
            url = user_input[CONF_URL]

            try:
                session = async_get_clientsession(self.hass)
                session.auth = BasicAuth(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                session.get(f"{url}/redfish/v1", raise_for_status=True)
            except (ClientTimeout, HTTPError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=url,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=REDFISH_SCHEMA,
            errors=errors,
        )
