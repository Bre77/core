"""Calendar platform for Teslemetry integration."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TeslemetryConfigEntry
from .entity import TeslemetryVehiclePollingEntity
from .models import TeslemetryVehicleData

PARALLEL_UPDATES = 0


def get_rrule_days(days_of_week: int) -> list[str]:
    """Get the rrule days for a days_of_week binary."""
    rrule_days_map = {
        0b0000001: "MO",
        0b0000010: "TU",
        0b0000100: "WE",
        0b0001000: "TH",
        0b0010000: "FR",
        0b0100000: "SA",
        0b1000000: "SU",
    }
    return [
        day_code
        for day_flag, day_code in rrule_days_map.items()
        if days_of_week & day_flag
    ]


def test_days_of_week(date: datetime, days_of_week: int) -> bool:
    """Check if a specific day is in the days_of_week binary."""
    return (days_of_week & (1 << date.weekday())) > 0


@dataclass
class Schedule:
    """A schedule for a vehicle."""

    name: str
    start_mins: timedelta
    end_mins: timedelta
    days_of_week: int
    uid: str
    location: str
    rrule: str | None = None

    def generate_upcoming_events(
        self, start_dt: datetime, end_dt: datetime
    ) -> Generator[CalendarEvent]:
        """Generate CalendarEvent objects within the time range [start_dt, end_dt)."""
        current_day = dt_util.start_of_local_day(start_dt)

        while current_day < end_dt:
            if test_days_of_week(current_day, self.days_of_week):
                event_start = current_day + self.start_mins
                event_end = current_day + self.end_mins

                if event_start < end_dt and event_end > start_dt:
                    yield CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=self.name,
                        description=self.location,
                        location=self.location,
                        uid=self.uid,
                        rrule=self.rrule,
                    )

            current_day += timedelta(days=1)


async def async_get_sorted_schedule_events(
    schedules: list[Schedule], start_dt: datetime, end_dt: datetime
) -> list[CalendarEvent]:
    """Fetch events from multiple schedules and return them sorted by start time."""
    all_events: list[CalendarEvent] = [
        event
        for schedule in schedules
        for event in schedule.generate_upcoming_events(start_dt, end_dt)
    ]
    return sorted(all_events, key=lambda event: event.start)


class TeslemetryChargeSchedule(TeslemetryVehiclePollingEntity, CalendarEntity):
    """Vehicle charge schedule calendar."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, data: TeslemetryVehicleData) -> None:
        """Initialize the charge schedule calendar."""
        self.schedules: list[Schedule] = []
        self.summary_format = (
            f"Charge scheduled for {data.device.get('name', 'Vehicle')}"
        )
        super().__init__(data, "charge_schedule_data_charge_schedules")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        next_event: CalendarEvent | None = None
        future_limit = now + timedelta(days=14)

        for schedule in self.schedules:
            first_occurrence = next(
                schedule.generate_upcoming_events(now, future_limit), None
            )
            if first_occurrence and (
                next_event is None or first_occurrence.start < next_event.start
            ):
                next_event = first_occurrence

        return next_event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return await async_get_sorted_schedule_events(
            self.schedules, start_date, end_date
        )

    def _async_update_attrs(self) -> None:
        """Update the calendar events by parsing raw schedule data."""
        raw_schedules_data = self._value or []
        self.schedules = []
        for schedule_data in raw_schedules_data:
            if not schedule_data.get("enabled") or not schedule_data.get(
                "days_of_week"
            ):
                continue

            start_time_min = schedule_data.get("start_time", 0)
            end_time_min = schedule_data.get("end_time", 0)
            start_enabled = schedule_data.get("start_enabled", True)
            end_enabled = schedule_data.get("end_enabled", True)

            if not end_enabled:
                start_mins = timedelta(minutes=start_time_min)
                end_mins = start_mins
            elif not start_enabled:
                end_mins = timedelta(minutes=end_time_min)
                start_mins = end_mins
            elif start_time_min > end_time_min:
                start_mins = timedelta(minutes=start_time_min)
                end_mins = timedelta(days=1, minutes=end_time_min)
            else:
                start_mins = timedelta(minutes=start_time_min)
                end_mins = timedelta(minutes=end_time_min)

            days_of_week = schedule_data["days_of_week"]
            rrule_days = get_rrule_days(days_of_week)
            rrule = f"FREQ=WEEKLY;WKST=MO;BYDAY={','.join(rrule_days)}"

            if schedule_data.get("one_time"):
                rrule += ";COUNT=1"

            self.schedules.append(
                Schedule(
                    name=schedule_data.get("name") or self.summary_format,
                    start_mins=start_mins,
                    end_mins=end_mins,
                    days_of_week=days_of_week,
                    uid=str(schedule_data.get("id", f"charge_{len(self.schedules)}")),
                    location=f"{schedule_data.get('latitude', '')},{schedule_data.get('longitude', '')}",
                    rrule=rrule,
                )
            )
        self._attr_available = bool(self.schedules)


class TeslemetryPreconditionSchedule(TeslemetryVehiclePollingEntity, CalendarEntity):
    """Vehicle precondition schedule calendar."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, data: TeslemetryVehicleData) -> None:
        """Initialize the precondition schedule calendar."""
        self.schedules: list[Schedule] = []
        self.summary_format = (
            f"Precondition scheduled for {data.device.get('name', 'Vehicle')}"
        )
        super().__init__(data, "preconditioning_schedule_data_precondition_schedules")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        next_event: CalendarEvent | None = None
        future_limit = now + timedelta(days=14)

        for schedule in self.schedules:
            first_occurrence = next(
                schedule.generate_upcoming_events(now, future_limit), None
            )
            if first_occurrence and (
                next_event is None or first_occurrence.start < next_event.start
            ):
                next_event = first_occurrence

        return next_event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return await async_get_sorted_schedule_events(
            self.schedules, start_date, end_date
        )

    def _async_update_attrs(self) -> None:
        """Update the calendar events by parsing raw schedule data."""
        raw_schedules_data = self._value or []
        self.schedules = []
        for schedule_data in raw_schedules_data:
            if not schedule_data.get("enabled") or not schedule_data.get(
                "days_of_week"
            ):
                continue

            precondition_time_min = schedule_data.get("precondition_time", 0)
            start_mins = timedelta(minutes=precondition_time_min)
            end_mins = start_mins

            days_of_week = schedule_data["days_of_week"]
            rrule = None
            if not schedule_data.get("one_time"):
                rrule_days = get_rrule_days(days_of_week)
                rrule = f"FREQ=WEEKLY;WKST=MO;BYDAY={','.join(rrule_days)}"

            self.schedules.append(
                Schedule(
                    name=schedule_data.get("name") or self.summary_format,
                    start_mins=start_mins,
                    end_mins=end_mins,
                    days_of_week=days_of_week,
                    uid=str(
                        schedule_data.get("id", f"precondition_{len(self.schedules)}")
                    ),
                    location=f"{schedule_data.get('latitude', '')},{schedule_data.get('longitude', '')}",
                    rrule=rrule,
                )
            )
        self._attr_available = bool(self.schedules)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeslemetryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Teslemetry calendar platform from a config entry."""
    entities: list[CalendarEntity] = []
    entities.extend(
        TeslemetryChargeSchedule(vehicle) for vehicle in entry.runtime_data.vehicles
    )
    entities.extend(
        TeslemetryPreconditionSchedule(vehicle)
        for vehicle in entry.runtime_data.vehicles
    )
    async_add_entities(entities)
