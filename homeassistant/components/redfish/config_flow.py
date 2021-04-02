"""Config Flow for Redfish integration."""
import logging

from aiohttp import BasicAuth
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

_LOGGER = logging.getLogger(__name__)


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
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()

            auth = BasicAuth(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            session = async_get_clientsession(self.hass, verify_ssl=False)

            async with session.get(f"{url}/redfish/v1/Systems", auth=auth) as resp:
                if resp.status != 200:
                    _LOGGER.warn(resp.status)
                    _LOGGER.warn(await resp.text())
                    errors["base"] = "cannot_connect"
                else:
                    user_input["ids"] = list(
                        map(
                            lambda x: x["@odata.id"].split("/")[-1],
                            (await resp.json())["Members"],
                        )
                    )

                    return self.async_create_entry(
                        title=url,
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=REDFISH_SCHEMA,
            errors=errors,
        )
