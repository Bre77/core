"""Climate platform for Climate Control integration."""
import datetime

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
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_AREA,
    CONF_CLIMATE_ENTITY,
    CONF_COVER_ENTITY,
    CONF_SENSOR_ENTITY,
    CONF_ZONES,
)

HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_AUTO]
TIME_TARGET = 120


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


class ClimateControlClimateEntity(RestoreEntity, ClimateEntity):
    """Climate Control Climate Entity."""

    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_target_temperature: float
    _attr_hvac_mode: str

    _sensor_delta: float
    _sensor_duration: float
    _cover_position: float
    _cover_last_changed: datetime.datetime
    _sensor_last_changed: datetime.datetime
    _climate_mode: str
    _climate_target: float

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

        # Private variables
        self._area = self.area_registry.async_get_area(area_id)
        # self.store = Store()

        # restored = self.store.async_load()

        self._climate_entity_id = climate_entity_id
        self._climate_entity = self.entity_registry.async_get(climate_entity_id)

        self._cover_entity_id = cover_entity_id
        # self.cover_entity = self.entity_registry.async_get(cover_entity_id)

        self._sensor_entity_id = sensor_entity_id
        # self.sensor_entity = self.entity_registry.async_get(sensor_entity_id)

        # Attributes
        self._attr_name = f"{getattr(self._area,'name')} Climate Control"

        self._attr_target_temperature_step = getattr(
            self._climate_entity, "capabilities"
        )[ATTR_TARGET_TEMP_STEP]
        self._attr_max_temp = getattr(self._climate_entity, "capabilities")[
            ATTR_MAX_TEMP
        ]
        self._attr_min_temp = getattr(self._climate_entity, "capabilities")[
            ATTR_MIN_TEMP
        ]
        self._attr_area_id = area_id

        async def event_listener(event):
            """Take action on state change events."""
            entity_id = event.data["entity_id"]
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")

            if new_state is not None and new_state.state != "unknown":
                if entity_id == self._climate_entity_id:
                    self._climate_mode = new_state.state
                    self._climate_target = new_state.attributes[TEMPERATURE]
                    return
                if entity_id == self._cover_entity_id:
                    if ATTR_CURRENT_POSITION in new_state.attributes:
                        self._cover_position = float(
                            new_state.attributes[ATTR_CURRENT_POSITION]
                        )
                    elif new_state.state == STATE_OPEN:
                        self._cover_position = 100
                    elif new_state.state == STATE_CLOSED:
                        self._cover_position = 0

                    _cover_last_changed = new_state.last_changed
                    return
                if entity_id == sensor_entity_id:
                    try:
                        new_value = float(new_state.state)
                    except ValueError:
                        return
                    self._attr_current_temperature = new_value
                    self._sensor_last_changed = new_state.last_changed
                    try:
                        old_value = float(old_state.state)
                    except ValueError:
                        return
                    self._sensor_delta = new_value - old_value
                    self._sensor_duration = (
                        new_state.last_changed - old_state.last_changed
                    ).total_seconds()
                    print(self._sensor_delta, self._sensor_duration)
                    hass.async_create_task(self._run())
                    return

        hass.bus.async_listen(EVENT_STATE_CHANGED, event_listener)

    async def async_added_to_hass(self):
        """Handle entity which will be added and restore its state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._attr_hvac_mode = state.state
            self._attr_target_temperature = state.attributes["temperature"]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""
        self._attr_hvac_mode = hvac_mode
        # Run immediately when enabled
        if hvac_mode == HVAC_MODE_AUTO:
            self.hass.async_create_task(self._run())

    async def async_set_temperature(self, **kwargs):
        """Set the target temperature."""
        self._attr_target_temperature = kwargs.get(ATTR_TEMPERATURE)

    async def _run(self):
        """Run the automatic climate control."""
        if self._attr_hvac_mode != HVAC_MODE_AUTO:
            return

        self.climate_mode = HVAC_MODE_COOL  # TEST
        if self.climate_mode == HVAC_MODE_COOL:
            mode = -1
        elif self.climate_mode == HVAC_MODE_HEAT:
            mode = 1
        else:
            print(f"Unknown HVAC mode {self.climate_mode}")
            return

        # temp / sec
        rate_of_change = self._sensor_delta / self._sensor_duration
        future = rate_of_change * TIME_TARGET
        # change in degrees
        change_required = self._attr_target_temperature - self._attr_current_temperature
        action = (change_required - future) * mode
        print(rate_of_change, future, change_required, action, position)

        position = round(self._cover_position + (action * 5))
        print(rate_of_change, future, change_required, action, position)
        # print(change, position, self._cover_entity_id, min(100, max(0, position)))

        await self.hass.services.async_call(
            COVER,
            SERVICE_SET_COVER_POSITION,
            {
                ATTR_ENTITY_ID: [self._cover_entity_id],
                ATTR_POSITION: min(100, max(0, position)),
            },
        )
