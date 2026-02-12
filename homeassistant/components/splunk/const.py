"""Constants for the Splunk integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entityfilter import EntityFilter

DOMAIN = "splunk"

type SplunkConfigEntry = ConfigEntry[EntityFilter]

CONF_FILTER = "filter"

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8088
DEFAULT_SSL = False
DEFAULT_NAME = "HASS"
