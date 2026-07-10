# Teslemetry integration notes

## Sharp edges

- **Bluetooth-first command routing.** When a vehicle subentry is paired (its
  data carries a BLE `address`) and the vehicle is in range,
  `_async_resolve_vehicle_api` wraps the cloud `Vehicle` in a `tesla_fleet_api`
  `VehicleRouter` that tries the local `VehicleBluetooth` first and fails over to
  cloud on any error. `VehicleBluetooth` is constructed with `verify_commands=True`,
  so a mutating BLE command that times out is resolved by reading vehicle state
  before the Router fails over, keeping failover safe for non-idempotent commands.
  Do not add a blind retry around a routed command, and catch `TeslaFleetError` (a
  `BaseException` subclass, not `Exception`) around BLE calls - `handle_command`
  and the config flow already do.
- The full BLE behavior catalogue (verify-by-state, wake boot-delay, response-size
  caps, per-command quirks) lives in the `tesla_fleet_api` library's `AGENTS.md`;
  consult it before changing anything on the BLE command path.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
