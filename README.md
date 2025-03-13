# Tesla Bluetooth

Home Assistant integration for communicating with Tesla vehicles over BLE

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Teslemetry&repository=hass-tesla-bluetooth)

## Important Notice

This integration will keep your vehicle awake constantly while connected. If you want your vehicle to sleep, I recommend creating an automation to enable and disable the included "polling" switch.

The recommended logic is:
- Trigger status is On: Switch Polling On
- Trigger sentry mode, charging, user present, where all are off: Switch Polling Off

## Limitations

- Tesla vehicles only support 3 BLE connections, which includes the mobile app, watch app, and Powerwall when Charge On Solar is enabled.
- This will not work with legacy (pre-2021) Model S and Model X vehicles.
- This will not work if the Tesla Fleet, Tessie, or Teslemetry (core version) integrations are configured in Home Assistant.
- It will work alongside the latest Teslemetry Custom (HACS version) integration, but both need to be kept up to date to ensure library compatibility.
- This is a work in progress, lower your expectations.

## Known Issues

Initial setup may fail after the virtual key is installed. Simply retry the setup and the pairing step will be skipped.

The entities will go unavailable if your vehicle is not connected or the communication otherwise fails in an unexpected way.

## Troubleshooting a vehicle not being discovered.

- Ensure the Bluetooth integration is configured.
- Ensure your Bluetooth hardware is close enough to your vehicle. Using Bluetooth proxies near the vehicle is recommended
- Ensure you do not have more than 2 other active BLE connections. Turn Bluetooth off on devices running the Tesla or Tessie app including watches.
- Be patient, discovery won't be instantaneous.