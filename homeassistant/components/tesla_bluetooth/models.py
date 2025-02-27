"""Data class for Tesla Bluetooth configuration."""

import asyncio
from dataclasses import dataclass

from tesla_fleet_api.tesla.vehicle.bluetooth import VehicleBluetooth

from .coordinator import TesleBluetoothCoordinators


@dataclass
class TeslaBluetoothConfigData:
    """Data class for Tesla Bluetooth configuration."""

    vin: str
    address: str


@dataclass
class TeslaBluetoothData:
    """Data class for Tesla Bluetooth data."""

    vehicle: VehicleBluetooth
    coordinators: TesleBluetoothCoordinators
    wakelock = asyncio.Lock()
