"""Config Flow for Teslemetry integration."""

from collections.abc import Mapping
import logging
from typing import Any, override

from aiohttp import ClientConnectionError
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from tesla_fleet_api.exceptions import (
    InvalidToken,
    NotOnWhitelistFault,
    SubscriptionRequired,
    TeslaFleetError,
)
from tesla_fleet_api.tesla.bluetooth import TeslaBluetooth
from tesla_fleet_api.tesla.vehicle.bluetooth import SERVICE_UUID, VehicleBluetooth
from tesla_fleet_api.teslemetry import Teslemetry
import voluptuous as vol

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CLIENT_ID,
    CONF_VIN,
    DOMAIN,
    LOGGER,
    PRIVATE_KEY_FILE,
    SUBENTRY_TYPE_VEHICLE,
)

# Number of pair() attempts before giving up and re-showing instructions.
BLE_PAIR_ATTEMPTS = 10


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Teslemetry OAuth2 authentication."""

    DOMAIN = DOMAIN
    VERSION = 2
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize config flow."""
        super().__init__()
        self.data: dict[str, Any] = {}
        self.uid: str | None = None

    @property
    @override
    def logger(self) -> logging.Logger:
        """Return logger."""
        return LOGGER

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the subentry types supported by this integration."""
        return {SUBENTRY_TYPE_VEHICLE: VehicleSubentryFlowHandler}

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow start."""
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential(CLIENT_ID, "", name="Teslemetry"),
        )
        return await super().async_step_user()

    @override
    async def async_oauth_create_entry(
        self,
        data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Handle OAuth completion and create config entry."""
        self.data = data

        # Test the connection with the OAuth token
        errors = await self.async_test_connection(data)
        if errors:
            return self.async_abort(reason="oauth_error")

        await self.async_set_unique_id(self.uid)
        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="reauth_account_mismatch")
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data=data
            )
        if self.source == SOURCE_RECONFIGURE:
            self._abort_if_unique_id_mismatch(reason="reconfigure_account_mismatch")
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(), data=data
            )
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Teslemetry",
            data=data,
        )

    async def async_test_connection(self, token_data: dict[str, Any]) -> dict[str, str]:
        """Test the connection with OAuth token."""
        access_token = token_data["token"]["access_token"]

        teslemetry = Teslemetry(
            session=async_get_clientsession(self.hass),
            access_token=access_token,
        )

        try:
            metadata = await teslemetry.metadata()
        except InvalidToken:
            return {"base": "invalid_access_token"}
        except SubscriptionRequired:
            return {"base": "subscription_required"}
        except ClientConnectionError:
            return {"base": "cannot_connect"}
        except TeslaFleetError as e:
            LOGGER.error("Teslemetry API error: %s", e)
            return {"base": "unknown"}

        self.uid = metadata["uid"]
        return {}

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth on failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={"name": "Teslemetry"},
            )

        return await super().async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        return await self.async_step_user()


class VehicleSubentryFlowHandler(ConfigSubentryFlow):
    """Pair a vehicle's virtual key over Bluetooth for local command routing.

    Reconfiguring a vehicle subentry walks the user through adding the
    integration's virtual key to the vehicle over BLE. Once paired, the BLE
    address is stored on the subentry, which enables Bluetooth-first command
    routing for that vehicle on the next reload.
    """

    def __init__(self) -> None:
        """Initialize the vehicle subentry flow."""
        self._vin: str | None = None
        self._address: str | None = None
        self._vehicle: VehicleBluetooth | None = None
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reject manual creation; vehicles come from the Teslemetry account."""
        return self.async_abort(reason="not_supported")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Start Bluetooth pairing for the selected vehicle."""
        self._vin = self._get_reconfigure_subentry().data[CONF_VIN]
        return await self.async_step_scan()

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Find the vehicle over Bluetooth and connect to it."""
        assert self._vin is not None

        if user_input is not None:
            parent = TeslaBluetooth()  # type: ignore[no-untyped-call]
            # The advertised BLE name is a hash of the VIN; match on its prefix.
            expected = parent.get_name(self._vin)[:17]
            for info in async_discovered_service_info(self.hass, connectable=True):
                if info.name and info.name.startswith(expected):
                    self._address = info.address
                    if error := await self._async_connect(info.device):
                        return self.async_show_form(
                            step_id="scan",
                            errors={"base": error},
                            description_placeholders={"vin": self._vin},
                        )
                    return await self.async_step_pair()
            # The advertised name is not always the VIN hash (e.g. Core Bluetooth
            # surfaces the display name), so let the user pick from nearby vehicles.
            return await self.async_step_pick()

        return self.async_show_form(
            step_id="scan",
            description_placeholders={"vin": self._vin},
        )

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Let the user pick their vehicle from nearby Tesla Bluetooth devices."""
        assert self._vin is not None

        if user_input is not None:
            info = self._discovered[user_input[CONF_ADDRESS]]
            self._address = info.address
            if error := await self._async_connect(info.device):
                return self._async_show_pick({"base": error})
            return await self.async_step_pair()

        self._discovered = {
            info.address: info
            for info in async_discovered_service_info(self.hass, connectable=True)
            if SERVICE_UUID in info.service_uuids
        }
        if not self._discovered:
            return self.async_show_form(
                step_id="scan",
                errors={"base": "device_not_found"},
                description_placeholders={"vin": self._vin},
            )
        return self._async_show_pick()

    @callback
    def _async_show_pick(
        self, errors: dict[str, str] | None = None
    ) -> SubentryFlowResult:
        """Show the form listing nearby Tesla Bluetooth devices."""
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{info.name} ({address})"
                            for address, info in self._discovered.items()
                        }
                    )
                }
            ),
            errors=errors,
            description_placeholders={"vin": self._vin or ""},
        )

    async def _async_connect(self, device: BLEDevice) -> str | None:
        """Connect to a BLE device, returning an error key on failure."""
        assert self._vin is not None
        parent = TeslaBluetooth()  # type: ignore[no-untyped-call]
        await parent.get_private_key(self.hass.config.path(PRIVATE_KEY_FILE))
        self._vehicle = parent.vehicles.createBluetooth(self._vin, device=device)
        try:
            await self._vehicle.connect()
        except (BleakError, TeslaFleetError, TimeoutError) as err:
            LOGGER.error("Failed to connect over Bluetooth: %s", err)
            return "cannot_connect"
        return None

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Check whether the virtual key is already whitelisted on the vehicle."""
        assert self._vehicle is not None
        try:
            await self._vehicle.handshakeVehicleSecurity()
        except NotOnWhitelistFault:
            return await self.async_step_instructions()
        except TeslaFleetError as err:
            LOGGER.error("Bluetooth security handshake failed: %s", err)
            return await self._async_abort("cannot_connect")
        return await self._async_finish()

    async def async_step_instructions(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Ask the user to approve the virtual key on the vehicle touchscreen."""
        if user_input is not None:
            return await self.async_step_authorize()
        return self.async_show_form(
            step_id="instructions",
            description_placeholders={"vin": self._vin or ""},
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Send the virtual key to the vehicle, then re-check the whitelist."""
        assert self._vehicle is not None
        for attempt in range(BLE_PAIR_ATTEMPTS):
            LOGGER.debug("Bluetooth pair attempt %s", attempt + 1)
            try:
                await self._vehicle.pair()
            except (BleakError, TeslaFleetError, TimeoutError) as err:
                LOGGER.debug("Pair attempt failed: %s", err)
                continue
            return await self.async_step_pair()
        return self.async_show_form(step_id="instructions", errors={"base": "timeout"})

    async def _async_finish(self) -> SubentryFlowResult:
        """Persist the paired BLE address and reload the entry."""
        assert self._vehicle is not None
        assert self._address is not None
        await self._vehicle.disconnect()
        entry = self._get_entry()
        self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_update_and_abort(
            entry,
            self._get_reconfigure_subentry(),
            data_updates={CONF_ADDRESS: self._address},
        )

    async def _async_abort(self, reason: str) -> SubentryFlowResult:
        """Disconnect any open BLE connection and abort the flow."""
        if self._vehicle is not None:
            await self._vehicle.disconnect()
        return self.async_abort(reason=reason)
