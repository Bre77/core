"""Local BLE data source for Teslemetry vehicles.

Values here come only from the vehicle's own Bluetooth link: unsolicited VCSEC
``VehicleStatus`` broadcasts, and (in later platforms) parked INFO reads. Once a
vehicle is BLE paired, its rerouted entities are strictly local - they go
unavailable on link loss and never fall back to a stream or cloud value.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, override

from tesla_fleet_api.tesla.vehicle.bluetooth import VehicleBluetooth

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .entity import TeslemetryRootEntity
from .models import TeslemetryVehicleData

# Poll only local process state to notice an unexpected link drop; the library
# has no connection-status callback yet. This issues no GATT call and never
# reconnects, scans, or wakes the vehicle.
CONNECTION_WATCH_INTERVAL = timedelta(seconds=5)

type BroadcastRegister = Callable[
    [VehicleBluetooth, Callable[[Any], None]], Callable[[], None]
]


class TeslemetryBLEDataManager:
    """Own a vehicle's direct Bluetooth link and its broadcast-sourced state.

    Broadcasts only arrive while the link a command opened is still up, so a
    value is valid only within the connection generation it was received in. An
    unexpected drop bumps the generation, which makes every previously received
    value stale and its entity unavailable.
    """

    def __init__(
        self, hass: HomeAssistant, bluetooth: VehicleBluetooth, vin: str
    ) -> None:
        """Initialize the manager around an already-created BLE client."""
        self.hass = hass
        self.vin = vin
        self._bluetooth = bluetooth
        self._generation = 0
        self._connected = False
        self._connection_listeners: list[Callable[[], None]] = []
        self._unsub_watcher: Callable[[], None] | None = None

    @property
    def bluetooth(self) -> VehicleBluetooth:
        """Return the direct BLE client, never the command router."""
        return self._bluetooth

    @property
    def generation(self) -> int:
        """Return the current connection generation."""
        return self._generation

    @property
    def connected(self) -> bool:
        """Return whether the BLE link is currently up."""
        return self._connected

    @callback
    def async_start(self) -> None:
        """Begin watching the link for an unexpected drop."""
        self._unsub_watcher = async_track_time_interval(
            self.hass, self._async_watch_connection, CONNECTION_WATCH_INTERVAL
        )

    @callback
    def async_stop(self) -> None:
        """Stop watching the link on unload."""
        if self._unsub_watcher is not None:
            self._unsub_watcher()
            self._unsub_watcher = None

    @callback
    def _async_watch_connection(self, now: datetime) -> None:
        """Reconcile the cached link state with the client's, invalidating on loss."""
        client = self._bluetooth.client
        connected = client is not None and client.is_connected
        if connected == self._connected:
            return
        # A drop makes every value received on the old link stale.
        if not connected:
            self._generation += 1
        self._connected = connected
        self._async_notify_connection()

    @callback
    def _async_notify_connection(self) -> None:
        """Tell every entity to re-evaluate availability."""
        for listener in list(self._connection_listeners):
            listener()

    @callback
    def async_on_connection_change(
        self, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback fired when the link comes up or drops."""
        self._connection_listeners.append(listener)

        @callback
        def remove() -> None:
            self._connection_listeners.remove(listener)

        return remove

    @callback
    def async_on_broadcast(
        self,
        register: BroadcastRegister,
        convert: Callable[[Any], Any],
        update: Callable[[Any, int], None],
    ) -> Callable[[], None]:
        """Subscribe an entity to one VCSEC broadcast field.

        ``register`` attaches the library's typed listener; ``convert`` maps the
        raw protobuf value to the entity value (``None`` for an unknown enum);
        ``update`` receives ``(value, generation)``.
        """

        @callback
        def handle(raw: Any) -> None:
            # A broadcast is itself proof the link is up, so surface it at once
            # rather than waiting up to a watch interval.
            if not self._connected:
                self._connected = True
                self._async_notify_connection()
            update(convert(raw), self._generation)

        return register(self._bluetooth, handle)


class TeslemetryVehicleBluetoothEntity(TeslemetryRootEntity):
    """Parent class for entities sourced from a vehicle's BLE broadcasts."""

    manager: TeslemetryBLEDataManager
    _value: Any = None
    _generation: int = -1

    def __init__(self, data: TeslemetryVehicleData, key: str) -> None:
        """Initialize common aspects of a Teslemetry BLE entity."""
        assert data.ble is not None
        self.vehicle = data
        self.manager = data.ble
        self.vin = data.vin
        self._attr_translation_key = key
        self._attr_unique_id = f"{data.vin}-{key}"
        self._attr_device_info = data.device

    @override
    async def async_added_to_hass(self) -> None:
        """Re-evaluate availability whenever the link comes up or drops."""
        self.async_on_remove(
            self.manager.async_on_connection_change(self._handle_connection_change)
        )

    @callback
    def _handle_connection_change(self) -> None:
        """Handle the link coming up or dropping."""
        self.async_write_ha_state()

    @callback
    def _handle_broadcast(self, value: Any, generation: int) -> None:
        """Store a freshly received broadcast value and its generation."""
        self._value = value
        self._generation = generation
        self.async_write_ha_state()

    @property
    @override
    def available(self) -> bool:
        """Return True only for a value received on the current live link."""
        return (
            self.manager.connected
            and self._generation == self.manager.generation
            and self._value is not None
        )
