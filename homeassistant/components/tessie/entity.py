"""Tessie parent entity class."""


from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODELS
from .coordinator import TessieDataUpdateCoordinator


class TessieEntity(CoordinatorEntity[TessieDataUpdateCoordinator]):
    """Parent class for Tessie Entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        key: str,
    ) -> None:
        """Initialize common aspects of a Tessie entity."""
        super().__init__(coordinator)
        self.vin: str = coordinator.vin
        self.key: str = key
        self.session: ClientSession = coordinator.session
        self._attr_unique_id = f"{self.vin}-{key}"

        if not hasattr(self, "_attr_translation_key"):
            self._attr_translation_key = key

        car_type = coordinator.data["vehicle_config-car_type"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.vin)},
            manufacturer="Tesla",
            configuration_url="https://my.tessie.com/",
            name=coordinator.data["display_name"],
            model=MODELS.get(car_type, car_type),
            sw_version=coordinator.data["vehicle_state-car_version"],
            hw_version=coordinator.data["vehicle_config-driver_assist"],
        )

    def get(self, key: str | None = None) -> Any:
        """Return value from coordinator data."""
        return self.coordinator.data[key or self.key]

    async def run(self, func: Callable, **kargs: Any):
        """Run a tessie_api function and handle exceptions."""
        try:
            response = await func(
                session=self.session,
                vin=self.vin,
                api_key=self.coordinator.api_key,
                **kargs,
            )
        except ClientResponseError as e:
            if e.status == HTTPStatus.INTERNAL_SERVER_ERROR:
                # Create issue for Virtual Key setup
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    "virtual_key",
                    is_fixable=True,
                    is_persistent=False,
                    learn_more_url="https://help.tessie.com/article/117-virtual-key",
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="virtual_key",
                )
            raise HomeAssistantError from e
        return response.get("result")

    def set(self, *args):
        """Set a value in coordinator data."""
        for key, value in args:
            self.coordinator.data[key] = value
        self.async_write_ha_state()
