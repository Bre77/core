"""Climate platform for Climate Control integration."""
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER,
    SERVICE_SET_COVER_POSITION,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    EVENT_STATE_CHANGED,
    STATE_CLOSED,
    STATE_OPEN,
    TEMP_CELSIUS,
    TEMPERATURE,
)
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.storage import Store

from .const import (
    CONF_AREA,
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    CONF_ZONES,
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
    """Climate Control Climate Entity."""

    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    store = Store

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
        self.hass = hass
        self.entity_registry = async_get_entity_registry(hass)
        self.area_registry = async_get_area_registry(hass)

        self.area = self.area_registry.async_get_area(area_id)
        # self.store = Store()

        # restored = self.store.async_load()

        self.climate_entity_id = climate_entity_id
        self.climate_entity = self.entity_registry.async_get(climate_entity_id)
        self.climate_mode = None
        self.climate_target = None

        print(self.climate_entity)
        print(hass.states.get(climate_entity_id))

        self.cover_entity_id = cover_entity_id
        self.cover_entity = self.entity_registry.async_get(cover_entity_id)
        self.cover_position = None
        print(self.cover_entity)
        print(hass.states.get(cover_entity_id))

        self.sensor_entity_id = sensor_entity_id
        self.sensor_entity = self.entity_registry.async_get(sensor_entity_id)

        print(self.sensor_entity)
        print(hass.states.get(sensor_entity_id))

        self._attr_name = f"{self.area.get('name')} Climate Control"
        self._attr_temperature_unit = TEMP_CELSIUS  # This isn't right
        self._attr_target_temperature_step = self.climate_entity.capabilities[
            ATTR_TARGET_TEMP_STEP
        ]
        self._attr_max_temp = self.climate_entity.capabilities[ATTR_MAX_TEMP]
        self._attr_min_temp = self.climate_entity.capabilities[ATTR_MIN_TEMP]
        self._attr_area_id = area_id

        self._attr_hvac_mode = HVAC_MODE_AUTO  # This isn't right
        self._attr_target_temperature = 24  # This isn't right

        async def event_listener(event):
            """Take action on state change events."""
            state = event.data.get("new_state")
            if state is not None and state.state != "unknown":
                if state.entity_id == climate_entity_id:
                    print(state.entity_id, state.state, state.attributes)
                    self.climate_mode = state.state
                    self.climate_target = state.attributes[TEMPERATURE]
                    return
                if state.entity_id == cover_entity_id:
                    print(state.entity_id, state.attributes)
                    if ATTR_CURRENT_POSITION in state.attributes:
                        self.cover_position = float(
                            state.attributes[ATTR_CURRENT_POSITION]
                        )
                    elif state.state == STATE_OPEN:
                        self.cover_position = 100
                    elif state.state == STATE_CLOSED:
                        self.cover_position = 0
                    return
                if state.entity_id == sensor_entity_id:
                    try:
                        _state = float(state.state)
                    except ValueError:
                        return
                    self._attr_current_temperature = _state
                    print(state.entity_id, state.state, _state)
                    hass.async_create_task(self._run())
                    return

        hass.bus.async_listen(EVENT_STATE_CHANGED, event_listener)

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC Mode and State."""
        self._attr_hvac_mode = hvac_mode
        self.hass.async_create_task(self._run())

    async def async_set_temperature(self, **kwargs):
        """Set the Target Temperature."""
        self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)
        self.hass.async_create_task(self._run())

    async def _run(self):
        """Run the automatic climate control"""
        # Positive numbers open damper, negative numbers close it
        self.climate_mode = HVAC_MODE_COOL  # TEST
        if self.climate_mode == HVAC_MODE_COOL:
            change = self._attr_current_temperature - self._attr_target_temperature
        elif self.climate_mode == HVAC_MODE_HEAT:
            change = self._attr_target_temperature - self._attr_current_temperature
        else:
            return

        position = round(self.cover_position + (change * 5))
        print(change, position, self.cover_entity_id, min(100, max(0, position)))

        # self.climate_target
        # 24 - 25

        await self.hass.services.async_call(
            COVER,
            SERVICE_SET_COVER_POSITION,
            {
                ATTR_ENTITY_ID: [self.cover_entity_id],
                ATTR_POSITION: min(100, max(0, position)),
            },
        )
