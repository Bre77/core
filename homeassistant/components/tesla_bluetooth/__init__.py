"""Tesla Bluetooth integration."""

from os.path import exists
from typing import Final

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, LOGGER, PRIVATE_KEY_FILE

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS: Final = []
type TeslaBluetoothConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: TeslaBluetoothConfigEntry) -> bool:
    """Set up the Tesla Bluetooth integration."""

    if not exists(PRIVATE_KEY_FILE):
        hass.data[DOMAIN] = ec.generate_private_key(ec.SECP256R1(), default_backend())
        # save the key
        pem = hass.data[DOMAIN].private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(PRIVATE_KEY_FILE, "wb") as pem_out:
            pem_out.write(pem)
            LOGGER.info("Generated private key: %s", PRIVATE_KEY_FILE)
    else:
        try:
            with open(PRIVATE_KEY_FILE, "rb") as key_file:
                hass.data[DOMAIN] = serialization.load_pem_private_key(
                    key_file.read(), password=None, backend=default_backend()
                )
        except:
            # FATAL
            pass

    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up the Tesla Bluetooth configuration."""

    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload TeslaFleet Config."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
