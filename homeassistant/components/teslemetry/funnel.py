"""Observation funnel for Teslemetry vehicles.

One :class:`ObservationFunnel` per BLE-paired vehicle fans values from the
library's ``BleBroadcastPublisher`` into a single listener set. The funnel can
hold more than one source, but only the BLE publisher is attached today. The
funnel itself never ties a value to a connection generation; while it is
single-source BLE, :class:`TeslemetryVehicleFunnelEntity` re-imposes the BLE
generation tie so a dropped link clears the value, matching ``ble.py``.
"""

from typing import TYPE_CHECKING, override

from tesla_fleet_api.funnel import BleBroadcastPublisher, FieldPath, ObservationFunnel
from tesla_fleet_api.router import VehicleRouter
from tesla_fleet_api.tesla.vehicle.bluetooth import VehicleBluetooth
from tesla_fleet_api.teslemetry import Vehicle

from homeassistant.core import callback

from .entity import TeslemetryRootEntity
from .models import TeslemetryVehicleData

if TYPE_CHECKING:
    from . import TeslemetryConfigEntry
    from .ble import TeslemetryBLEDataManager


@callback
def async_setup_funnel(
    entry: TeslemetryConfigEntry,
    bluetooth: VehicleBluetooth,
) -> ObservationFunnel:
    """Build a vehicle's funnel and attach the BLE broadcast publisher.

    Returns the funnel; the publisher's teardown is registered on
    ``entry.async_on_unload`` so no publisher or listener survives an unload.
    The BLE publisher's own request/release (driven by
    :meth:`ObservationFunnel.listen`) subscribes to the vehicle's broadcasts
    only while a field is listened to.
    """
    funnel = ObservationFunnel()
    entry.async_on_unload(funnel.attach(BleBroadcastPublisher(bluetooth)))
    return funnel


class TeslemetryVehicleFunnelEntity(TeslemetryRootEntity):
    """Parent class for an entity served one field by the vehicle's funnel.

    A funnelled value is tied to the BLE connection generation it arrived in: a
    link drop makes it stale and the entity unavailable, matching the local BLE
    path in ``ble.py``. The tie exists only because the funnel is single-source
    BLE until the stream publisher ships; remove it once a second source is
    attached and a value can outlive the BLE link.
    """

    api: Vehicle | VehicleRouter
    manager: TeslemetryBLEDataManager
    _value: bool | None = None
    _generation: int = -1

    def __init__(self, data: TeslemetryVehicleData, key: str, field: FieldPath) -> None:
        """Initialize common aspects of a funnel-backed entity."""
        assert data.funnel is not None
        assert data.ble is not None
        self.funnel = data.funnel
        self.manager = data.ble
        self._field = field
        # Commands still route through the router; only reads are funnelled.
        self.api = data.api
        self.vin = data.vin
        self._attr_translation_key = key
        self._attr_unique_id = f"{data.vin}-{key}"
        self._attr_device_info = data.device

    @override
    async def async_added_to_hass(self) -> None:
        """Seed from the funnel's current value and subscribe to changes."""
        self._value = self.funnel.value(self._field)
        self._generation = self.manager.generation
        self._render_value()
        self.async_on_remove(self.funnel.listen(self._field, self._handle_value))
        self.async_on_remove(
            self.manager.async_on_connection_change(self._handle_connection_change)
        )

    @callback
    def _handle_value(self, value: bool | None) -> None:
        """Store a freshly funnelled value and its connection generation."""
        self._value = value
        self._generation = self.manager.generation
        self._render_value()
        self.async_write_ha_state()

    @callback
    def _handle_connection_change(self) -> None:
        """Re-evaluate availability when the link comes up or drops."""
        self.async_write_ha_state()

    def _render_value(self) -> None:
        """Render the current value into entity attributes."""

    @property
    @override
    def available(self) -> bool:
        """Return True only for a value received on the current live link."""
        return (
            self.manager.connected
            and self._generation == self.manager.generation
            and self._value is not None
        )
