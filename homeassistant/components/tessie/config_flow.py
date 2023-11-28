"""Config Flow for Advantage Air integration."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError
from tessie_api import get_state_of_all_vehicles
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

TESSIE_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


class AdvantageAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Tessie API connection."""

    VERSION = 1

    DOMAIN = DOMAIN

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Get configuration from the user."""
        errors = {}
        if user_input and CONF_API_KEY in user_input:
            try:
                data = await get_state_of_all_vehicles(
                    session=async_get_clientsession(self.hass),
                    api_key=user_input[CONF_API_KEY],
                )
            except ClientResponseError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_API_KEY])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=data["system"]["name"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=TESSIE_SCHEMA,
            errors=errors,
        )
