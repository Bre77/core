"""Support to send data to a EdgeHub."""
from datetime import datetime
import logging

from google.protobuf.timestamp_pb2 import Timestamp
import paho.mqtt.client as mqtt
from .sensors_pb2 import ExternalSensorAvailability, SensorChannel, SensorDatapoint

from homeassistant.const import (
    CONF_HOST,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, state as state_helper
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

DOMAIN = "edgehub"
DEFAULT_HOST = "localhost"
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Splunk component."""

    host = config[DOMAIN].get(CONF_HOST, DEFAULT_HOST)
    client = mqtt.Client()
    _LOGGER.info(f"Connecting to {host}:1883")
    client.connect(host, 1883, 5)
    _LOGGER.info(f"Connected to {host}:1883")

    entities = []

    async def edgehub_event_listener(event):
        """Listen for new messages on the bus and sends them to Splunk."""

        state = event.data.get("new_state")
        eid = event.data.get("entity_id")
        if state is None:
            return

        if not state.attributes.get("state_class", False):
            return

        try:
            value = state_helper.state_as_number(state)
        except ValueError:
            return

        # Send Available if required
        if eid not in entities:
            _LOGGER.info(f"Adding {eid} {state.name}")
            entities.append(eid)
            client.publish(
                "iotpuck/88e69537-27f0-4da1-89da-4e00fe90750c/sensors/availability",
                payload=ExternalSensorAvailability(
                    metrics=[eid],
                    type=state.name,
                    id=eid,
                    is_available=True,
                ).SerializeToString(),
            )

        client.publish(
            f"iotpuck/88e69537-27f0-4da1-89da-4e00fe90750c/sensors/{eid}/data",
            payload=SensorDatapoint(
                sensor_id=eid,
                timestamp=Timestamp().FromDatetime(state.last_changed),
                value=value,
                channel=SensorChannel(
                    name=eid,
                    unit=state.attributes.get("unit_of_measurement", ""),
                    type=state.name,
                ),
                is_sensor_enabled=True,
                is_anomaly_enabled=False,
            ).SerializeToString(),
        )

    hass.bus.async_listen(EVENT_STATE_CHANGED, edgehub_event_listener)

    return True
