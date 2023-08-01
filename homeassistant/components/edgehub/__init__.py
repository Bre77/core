"""Support to send data to a Splunk instance."""
from datetime import datetime
import logging

from google.protobuf.timestamp_pb2 import Timestamp
import paho.mqtt.client as mqtt
from sensors_pb2 import ExternalSensorAvailability, SensorChannel, SensorDatapoint

from homeassistant.const import (
    EVENT_STATE_CHANGED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, state as state_helper

_LOGGER = logging.getLogger(__name__)

DOMAIN = "edgehub"
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the Splunk component."""

    client = mqtt.Client()
    client.connect("localhost", 1883, 60)

    entities = []

    async def edgehub_event_listener(event):
        """Listen for new messages on the bus and sends them to Splunk."""

        state = event.data.get("new_state")
        if state is None:
            return

        try:
            value = state_helper.state_as_number(state)
        except ValueError:
            return

        # Send Available if required
        if event.data.entity_id not in entities:
            entities.append(event.data.entity_id)
            client.publish(
                "iotpuck/88e69537-27f0-4da1-89da-4e00fe90750c/sensors/availability",
                payload=ExternalSensorAvailability(
                    metrics=state["attributes"].get(
                        "friendly_name", event.data.entity_id
                    ),
                    type=state["attributes"].get("device_class", "homeassistant"),
                    id=event.data.entity_id,
                    is_available=True,
                ).SerializeToString(),
            )

        client.publish(
            f"iotpuck/88e69537-27f0-4da1-89da-4e00fe90750c/sensors/{event.data.entity_id}/data",
            payload=SensorDatapoint(
                sensor_id=event.data.entity_id,
                timestamp=Timestamp().FromDatetime(
                    datetime.fromisoformat(state["last_changed"])
                ),
                value=value,
                channel=SensorChannel(
                    name=state["attributes"].get("friendly_name", event.data.entity_id),
                    unit=state["attributes"].get("unit_of_measurement", ""),
                    type=state["attributes"].get("device_class", "homeassistant"),
                ),
                is_sensor_enabled=True,
                is_anomaly_enabled=False,
            ).SerializeToString(),
        )

    hass.bus.async_listen(EVENT_STATE_CHANGED, edgehub_event_listener)

    return True
