"""Provides diagnostics for Tesla Bluetooth."""

from __future__ import annotations

from typing import Any

from tesla_fleet_api.tesla.bluetooth import toDict

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import TeslaBluetoothConfigEntry

REDACT = [
    "id",
    "user_id",
    "vehicle_id",
    "vin",
    "tokens",
    "id_s",
    "latitude",
    "longitude",
]


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TeslaBluetoothConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    vehicle = entry.runtime_data.vehicle
    coordinators = entry.runtime_data.coordinators

    # Return only the relevant children
    return {
        "connected": bool(vehicle.client.is_connected),
        "coordinators": {
            x.kind: {
                "data": async_redact_data(toDict(x.data), REDACT) if x.data else None,
                "last_updated": x.last_update_success_time,
            }
            for x in coordinators
        },
    }
