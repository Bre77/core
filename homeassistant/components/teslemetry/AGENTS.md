# Teslemetry integration notes

## Sharp edges

- **Bluetooth-first command routing double-execution.** When a vehicle subentry
  is paired (its data carries a BLE `address`) and the vehicle is in range,
  `_async_resolve_vehicle_api` wraps the cloud `Vehicle` in a `tesla_fleet_api`
  `VehicleRouter` that tries the local `VehicleBluetooth` first and fails over to
  cloud on any error. A mutating BLE command that raises `BluetoothTimeout` is
  inconclusive - it may already have executed on the car - so the Router's
  failover can run a non-idempotent command twice (e.g. `actuate_trunk`,
  `media_toggle_playback`, `media_next_track`). This is accepted: nearly all of
  the routed commands are idempotent setters, and a per-command idempotency gate
  belongs in the library Router, not here. Do not add a blind retry around a
  routed command, and catch `TeslaFleetError` (a `BaseException` subclass, not
  `Exception`) around BLE calls - `handle_command` and the config flow already do.
- The full BLE behavior catalogue (verify-by-state, wake boot-delay, response-size
  caps, per-command quirks) lives in the `tesla_fleet_api` library's `AGENTS.md`;
  consult it before changing anything on the BLE command path.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
