"""Climate platform for Climate Control integration."""
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP,
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers import state as state_helper
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    CONF_AREA,
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    CONF_ZONES,
    DOMAIN,
)

HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_AUTO]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up ClimateControl climate platform."""

    entities = []
    for zone in config_entry.data[CONF_ZONES]:
        entities.append(
            ClimateControlClimateEntity(
                hass,
                config_entry.data[CONF_CLIMATE_ENTITY],
                zone[CONF_COVER_ENTITY],
                zone[CONF_SENSOR_ENTITY],
                zone[CONF_AREA],
            )
        )
    async_add_entities(entities)


class ClimateControlClimateEntity(ClimateEntity):

    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE

    def __init__(
        self,
        hass,
        climate_entity_id,
        cover_entity_id,
        sensor_entity_id,
        area_id,
    ) -> None:
        """Initialize a climate control entity."""
        super().__init__()
        # self.hass = hass
        self.entity_registry = async_get_entity_registry(hass)

        self.climate_entity_id = climate_entity_id
        self.climate_entity = self.entity_registry.async_get(climate_entity_id)
        print(self.climate_entity)

        self.cover_entity_id = cover_entity_id
        self.cover_entity = self.entity_registry.async_get(cover_entity_id)
        print(self.cover_entity)

        self.sensor_entity_id = sensor_entity_id
        self.sensor_entity = self.entity_registry.async_get(sensor_entity_id)
        print(self.sensor_entity)

        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_target_temperature_step = self.climate_entity.capabilities[
            ATTR_TARGET_TEMP_STEP
        ]
        self._attr_max_temp = self.climate_entity.capabilities[ATTR_MAX_TEMP]
        self._attr_min_temp = self.climate_entity.capabilities[ATTR_MIN_TEMP]
        self._attr_area_id = area_id

        # self._attr_device_info = {
        #    "identifiers": {(DOMAIN, self.coordinator.data["system"]["rid"])},
        #    "name": self.coordinator.data["system"]["name"],
        #    "manufacturer": "Advantage Air",
        #    "model": self.coordinator.data["system"]["sysType"],
        #    "sw_version": self.coordinator.data["system"]["myAppRev"],
        #    "area": self.area_id,
        # }

        # hass.bus.async_listen(EVENT_STATE_CHANGED, splunk_event_listener)

    property

    def current_temperature(self):
        """Return the current temperature."""
        return self.entity_registrysensor_entity
