"""Teslemetry parent entity class."""

import asyncio
from typing import Any

from tesla_fleet_api import EnergySpecific, VehicleSpecific
from tesla_fleet_api.exceptions import TeslaFleetError

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER, MODELS, TeslemetryState
from .coordinator import (
    TeslemetryEnergySiteInfoCoordinator,
    TeslemetryEnergySiteLiveCoordinator,
    TeslemetryVehicleDataCoordinator,
)
from .models import TeslemetryEnergyData, TeslemetryVehicleData


class TeslemetryEntity(
    CoordinatorEntity[
        TeslemetryVehicleDataCoordinator
        | TeslemetryEnergySiteLiveCoordinator
        | TeslemetryEnergySiteInfoCoordinator
    ]
):
    """Parent class for all Teslemetry entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TeslemetryVehicleDataCoordinator
        | TeslemetryEnergySiteLiveCoordinator
        | TeslemetryEnergySiteInfoCoordinator,
        api: VehicleSpecific | EnergySpecific,
        key: str,
    ) -> None:
        """Initialize common aspects of a Teslemetry entity."""
        super().__init__(coordinator)
        self.api = api
        self.key = key
        self._attr_translation_key = key
        self._update()

    def get(self, key: str | None = None, default: Any | None = None) -> Any:
        """Return a specific value from coordinator data."""
        return self.coordinator.data.get(key or self.key, default)

    def exactly(self, value: Any, key: str | None = None) -> bool | None:
        """Return if a key exactly matches the value, but retain None."""
        if value is None:
            return self.get(key, False) is None
        current = self.get(key)
        if current is None:
            return None
        return current == value

    def set(self, *args: Any) -> None:
        """Set a value in coordinator data."""
        for key, value in args:
            self.coordinator.data[key] = value
        self.async_write_ha_state()

    def has(self, key: str | None = None) -> bool:
        """Return True if a specific value is in coordinator data."""
        return (key or self.key) in self.coordinator.data

    def raise_for_scope(self):
        """Raise an error if a scope is not available."""
        if not self.scoped:
            raise ServiceValidationError(
                f"Missing required scope: {' or '.join(self.entity_description.scopes)}"
            )

    async def handle_command(self, command) -> dict[str, Any]:
        """Handle a command."""
        try:
            result = await command
            LOGGER.debug("Command result: %s", result)
        except TeslaFleetError as e:
            LOGGER.debug("Command error: %s", e.message)
            raise ServiceValidationError(
                f"Teslemetry command failed, {e.message}"
            ) from e
        return result

    def _update(self) -> None:
        """Update attributes with coordinator data."""
        pass

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update()
        super()._handle_coordinator_update()


class TeslemetryVehicleEntity(TeslemetryEntity):
    """Parent class for Teslemetry Vehicle entities."""

    def __init__(
        self,
        data: TeslemetryVehicleData,
        key: str,
    ) -> None:
        """Initialize common aspects of a Teslemetry entity."""
        super().__init__(data.coordinator, data.api, key)
        self._attr_unique_id = f"{data.vin}-{key}"
        self._wakelock = data.wakelock

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.vin)},
            manufacturer="Tesla",
            configuration_url="https://teslemetry.com/console",
            name=data.display_name,
            model=MODELS.get(data.vin[3]),
            serial_number=data.vin,
        )

    async def wake_up_if_asleep(self) -> None:
        """Wake up the vehicle if its asleep."""
        async with self._wakelock:
            times = 0
            while self.coordinator.data["state"] != TeslemetryState.ONLINE:
                try:
                    if times == 0:
                        cmd = await self.api.wake_up()
                    else:
                        cmd = await self.api.vehicle()
                    state = cmd["response"]["state"]
                except TeslaFleetError as e:
                    raise HomeAssistantError(str(e)) from e
                except TypeError as e:
                    raise HomeAssistantError("Invalid response from Teslemetry") from e
                self.coordinator.data["state"] = state
                if state != TeslemetryState.ONLINE:
                    times += 1
                    if times >= 4:  # Give up after 30 seconds total
                        raise HomeAssistantError("Could not wake up vehicle")
                    await asyncio.sleep(times * 5)

    async def handle_command(self, command) -> dict[str, Any]:
        """Handle a vehicle command."""
        result = await super().handle_command(command)
        if not (message := result.get("response", {}).get("result")):
            message = message or "Bad response from Tesla"
            LOGGER.debug("Command failure: %s", message)
            raise ServiceValidationError(message)
        return result


class TeslemetryEnergyLiveEntity(TeslemetryEntity):
    """Parent class for Teslemetry Energy Site Live entities."""

    def __init__(
        self,
        data: TeslemetryEnergyData,
        key: str,
    ) -> None:
        """Initialize common aspects of a Teslemetry entity."""
        super().__init__(data.live_coordinator, data.api, key)
        self._attr_unique_id = f"{data.id}-{key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(data.id))},
            manufacturer="Tesla",
            configuration_url="https://teslemetry.com/console",
            name=self.coordinator.data.get("site_name", "Energy Site"),
        )


class TeslemetryEnergyInfoEntity(TeslemetryEntity):
    """Parent class for Teslemetry Energy Site Info Entities."""

    def __init__(
        self,
        data: TeslemetryEnergyData,
        key: str,
    ) -> None:
        """Initialize common aspects of a Teslemetry entity."""
        super().__init__(data.info_coordinator, data.api, key)
        self._attr_unique_id = f"{data.id}-{key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(data.id))},
            manufacturer="Tesla",
            configuration_url="https://teslemetry.com/console",
            name=self.coordinator.data.get("site_name", "Energy Site"),
        )
