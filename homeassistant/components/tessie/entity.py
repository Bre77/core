"""Tessie parent entity class."""


from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODELS, TessieCategory, TessieKey
from .coordinator import TessieDataUpdateCoordinator


class TessieEntity(CoordinatorEntity[TessieDataUpdateCoordinator]):
    """Parent class for Tessie Entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TessieDataUpdateCoordinator,
        vin: str,
        category: str,
        key: str,
    ) -> None:
        """Initialize common aspects of a Tessie entity."""
        super().__init__(coordinator)
        self.vin: str = vin
        self.category: str = category
        self.key: str = key
        self.session: ClientSession = coordinator.session

        car_data = coordinator.data[vin]
        car_type = car_data[TessieCategory.VEHICLE_CONFIG]["car_type"]

        self._attr_translation_key = key
        self._attr_unique_id = f"{vin}:{category}:{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            manufacturer="Tesla",
            configuration_url="https://my.tessie.com/",
            name=car_data[TessieKey.DISPLAY_NAME],
            model=MODELS.get(car_type, car_type),
            sw_version=car_data[TessieCategory.VEHICLE_STATE]["car_version"],
            hw_version=car_data[TessieCategory.VEHICLE_CONFIG]["driver_assist"],
        )

    def get(self, key: str | None = None) -> Any:
        """Return value from coordinator data."""
        return self.coordinator.data[self.vin][self.category][key or self.key]

    async def run(self, func: Callable, **kargs: Any):
        """Run a tessie_api function and handle exceptions."""
        try:
            return await func(
                session=self.session,
                vin=self.vin,
                api_key=self.coordinator.api_key,
                **kargs,
            )["result"]
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

    async def set(self, *args):
        """Set a value in coordinator data."""
        for key, value in args:
            self.coordinator.data[self.vin][self.category][key] = value
        self.async_write_ha_state()
