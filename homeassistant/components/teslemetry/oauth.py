"""Provide oauth implementations for the Teslemetry integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import AUTHORIZE_URL, TOKEN_URL


class TeslemetryImplementation(
    config_entry_oauth2_flow.LocalOAuth2ImplementationWithPkce
):
    """Teslemetry OAuth2 implementation."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        client_id: str,
        refresh_token: str | None = None,
    ) -> None:
        """Initialize OAuth2 implementation."""

        super().__init__(
            hass,
            domain,
            client_id,
            AUTHORIZE_URL,
            TOKEN_URL,
        )
        self._refresh_token = refresh_token

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return "Teslemetry OAuth2"

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        data: dict = {
            "name": self.hass.config.location_name,
        }
        data.update(super().extra_authorize_data)
        return data

    @property
    def extra_token_resolve_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the token resolve request."""
        data: dict = {
            "name": self.hass.config.location_name,
        }
        if self._refresh_token:
            data["refresh_token"] = self._refresh_token
        data.update(super().extra_token_resolve_data)
        return data
