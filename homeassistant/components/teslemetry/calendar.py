"""Calendar platform for Teslemetry integration."""

from collections.abc import Generator
from datetime import datetime, timedelta

from tesla_fleet_api.const import Scope

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TeslemetryConfigEntry
from .entity import TeslemetryVehiclePollingEntity
from .models import TeslemetryVehicleData


# Helper function to generate rrule day strings
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


class Schedule:
    """A schedule for a vehicle."""

    def __init__(
        self,
        name: str,
        start_mins: timedelta,
        end_mins: timedelta,
        days_of_week: int,
        uid: str,
        location: str,
        rrule: str | None = None,
    ) -> None:
        """Initialize schedule."""
        self.name = name
        self.start_mins = start_mins
        self.end_mins = end_mins
        self.days_of_week = days_of_week
        self.uid = uid
        self.location = location
        self.rrule = rrule

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
                        description=self.location,
                        location=self.location,
                        uid=self.uid,
                        rrule=self.rrule,
                    )

            # Move to the next day
            current_day += timedelta(days=1)


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
    all_events: list[CalendarEvent] = [
        event
        for schedule in schedules
        for event in schedule.generate_upcoming_events(start_dt, end_dt)
    ]

    # Sort the collected events by their start time
    return sorted(all_events, key=lambda event: event.start)


class TeslemetryChargeSchedule(TeslemetryVehiclePollingEntity, CalendarEntity):
    """Vehicle Charge Schedule Calendar."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        data: TeslemetryVehicleData,
        scopes: list[Scope],
    ) -> None:
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

        # Define a reasonable future limit for finding the 'next' event (e.g., 14 days)
        future_limit = now + timedelta(days=14)

        for schedule in self.schedules:
            # Use the generator to find the first event for this schedule after 'now'
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

            start_time_min = schedule_data.get("start_time", 0)
            end_time_min = schedule_data.get("end_time", 0)
            start_enabled = schedule_data.get("start_enabled", True)
            end_enabled = schedule_data.get("end_enabled", True)

            # Determine start and end timedeltas based on enabled flags and times
            if not end_enabled:
                start_mins = timedelta(minutes=start_time_min)
                end_mins = start_mins  # Treat as instantaneous if end is disabled
            elif not start_enabled:
                end_mins = timedelta(minutes=end_time_min)
                start_mins = end_mins  # Treat as instantaneous if start is disabled
            elif start_time_min > end_time_min:
                # Crosses midnight
                start_mins = timedelta(minutes=start_time_min)
                end_mins = timedelta(days=1, minutes=end_time_min)
            else:
                # Same day
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeslemetryConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Teslemetry Calendar platform from a config entry."""

    entities_to_add: list[CalendarEntity] = []

    # Vehicle Charge Schedules
    entities_to_add.extend(
        TeslemetryChargeSchedule(vehicle, entry.runtime_data.scopes)
        for vehicle in entry.runtime_data.vehicles
    )

    async_add_entities(entities_to_add)
