"""Calendar platform for Teslemetry integration."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta

from tesla_fleet_api.const import Scope

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TeslemetryConfigEntry
from .entity import TeslemetryVehiclePollingEntity
from .models import TeslemetryVehicleData


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
    rrule_days = []
    for day_flag, day_code in rrule_days_map.items():
        if days_of_week & day_flag:
            rrule_days.append(day_code)
    return rrule_days


# Helper function to check if a date matches the days_of_week mask
def test_days_of_week(date: datetime, days_of_week: int) -> bool:
    """Check if a specific day is in the days_of_week binary."""
    return (days_of_week & (1 << date.weekday())) > 0


@dataclass
class Schedule:
    """A schedule for a vehicle or tariff."""

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
        """Generate CalendarEvent objects for this schedule occurring strictly within the time range [start_dt, end_dt).

        Args:
            start_dt: The inclusive start datetime of the query range.
            end_dt: The exclusive end datetime of the query range.

        Yields:
            CalendarEvent: Event objects for occurrences within the range.

        """
        # Start iterating from the beginning of the day of start_dt
        current_day = dt_util.start_of_local_day(start_dt)

        while current_day < end_dt:
            # Check if the schedule runs on this day of the week
            if test_days_of_week(current_day, self.days_of_week):
                # Calculate the event's start and end datetime for the current day
                event_start = current_day + self.start_mins
                event_end = current_day + self.end_mins

                # Check if the calculated event overlaps with the query range [start_dt, end_dt)
                if event_start < end_dt and event_end > start_dt:
                    yield CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=self.name,
                        description=self.location,  # Or a more specific description if available
                        location=self.location,
                        uid=self.uid,
                        rrule=self.rrule,
                    )

            # Move to the next day
            current_day += timedelta(days=1)

            # Optimization: If rrule indicates COUNT=1, stop after the first valid day found
            # However, the current rrule string doesn't reliably encode one-time nature
            # separate from days_of_week. Relying on the date iteration boundary is safer.
            # The original code had a `count < 7` check which is removed here in favor
            # of strictly adhering to start_dt and end_dt.


# Shared utility function to get sorted events from multiple schedules
async def async_get_sorted_schedule_events(
    schedules: list[Schedule], start_dt: datetime, end_dt: datetime
) -> list[CalendarEvent]:
    """Fetch events from multiple schedules within a time range and return them sorted by start time.

    Args:
        schedules: A list of Schedule objects.
        start_dt: The inclusive start datetime of the query range.
        end_dt: The exclusive end datetime of the query range.

    Returns:
        A list of CalendarEvent objects, sorted chronologically.

    """
    # Gather all events from all schedules within the given time range
    # This uses a nested list comprehension for conciseness.
    all_events: list[CalendarEvent] = [
        event
        for schedule in schedules
        for event in schedule.generate_upcoming_events(start_dt, end_dt)
    ]

    # Sort the collected events by their start time
    return sorted(all_events, key=lambda event: event.start)


class TeslemetryPreconditionSchedule(TeslemetryVehiclePollingEntity, CalendarEntity):
    """Vehicle Precondition Schedule Calendar."""

    _attr_entity_registry_enabled_default = False
    schedules: list[Schedule]
    summary_format: str

    def __init__(
        self,
        data: TeslemetryVehicleData,
        scopes: list[Scope],
    ) -> None:
        """Initialize the precondition schedule calendar."""
        self.schedules = []
        self.summary_format = (
            f"Precondition scheduled for {data.device.get('name', 'Vehicle')}"
        )
        super().__init__(data, "preconditioning_schedule_data_precondition_schedules")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        next_event: CalendarEvent | None = None
        future_limit = now + timedelta(days=14)  # Look ahead 14 days

        for schedule in self.schedules:
            try:
                first_occurrence = next(
                    schedule.generate_upcoming_events(now, future_limit), None
                )
            except StopIteration:
                first_occurrence = None

            if first_occurrence:
                if next_event is None or first_occurrence.start < next_event.start:
                    next_event = first_occurrence

        return next_event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range using the shared helper."""
        # Delegate to the shared function
        return await async_get_sorted_schedule_events(
            self.schedules, start_date, end_date
        )

    def _async_update_attrs(self) -> None:
        """Update the Calendar events by parsing raw schedule data."""
        raw_schedules_data = self._value or []
        self.schedules = []
        for schedule_data in raw_schedules_data:
            if not schedule_data.get("enabled") or not schedule_data.get(
                "days_of_week"
            ):
                continue

            # Preconditioning seems to be instantaneous based on original code
            precondition_time_min = schedule_data.get("precondition_time", 0)
            start_mins = timedelta(minutes=precondition_time_min)
            end_mins = start_mins  # Instantaneous event

            days_of_week = schedule_data["days_of_week"]
            rrule = None
            # Only set rrule if it's a recurring schedule
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
    """Set up the Teslemetry Calendar platform from a config entry."""

    entities_to_add: list[CalendarEntity] = []

    # Vehicle Precondition Schedules
    entities_to_add.extend(
        TeslemetryPreconditionSchedule(vehicle, entry.runtime_data.scopes)
        for vehicle in entry.runtime_data.vehicles
    )

    async_add_entities(entities_to_add)
