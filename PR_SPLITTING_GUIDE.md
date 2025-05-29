# Teslemetry Calendar PR Splitting Guide

This guide will help you split the large Teslemetry Calendar PR (#142894) into three smaller, focused pull requests that will be easier to review and merge.

## Overview

The original PR adds calendar platform support to Teslemetry with three distinct features:
1. **Energy Price Calendar entries** (Buy/Sell tariffs)
2. **Charging Schedule Calendar**
3. **Preconditioning Schedule Calendar**

## PR 1: Energy Price Calendar Entries

### Branch: `teslemetry-energy-price-calendar`

**Files to create/modify:**

1. **homeassistant/components/teslemetry/__init__.py**
   ```python
   # Add Platform.CALENDAR to PLATFORMS list
   PLATFORMS: Final = [
       Platform.BINARY_SENSOR,
       Platform.BUTTON,
       Platform.CALENDAR,  # Add this line
       Platform.CLIMATE,
       # ... rest of existing platforms
   ]
   ```

2. **homeassistant/components/teslemetry/calendar.py**
   - Include only TeslemetryTariffSchedule class and TariffPeriod dataclass
   - Include energy tariff related helper functions
   - async_setup_entry should only create TeslemetryTariffSchedule entities

3. **homeassistant/components/teslemetry/coordinator.py**
   ```python
   # In TeslemetryEnergyInfoCoordinator._async_update_data method:
   return flatten(
       data,
       exceptions=["daily_charges", "demand_charges", "energy_charges", "seasons"],
   )
   ```

4. **homeassistant/components/teslemetry/helpers.py**
   ```python
   def flatten(
       data: dict[str, Any], parent: str | None = None, exceptions: list[str] | None = None
   ) -> dict[str, Any]:
       """Flatten the data structure."""
       result = {}
       for key, value in data.items():
           exception = exceptions and key in exceptions
           if parent:
               key = f"{parent}_{key}"
           if isinstance(value, dict) and not exception:
               result.update(flatten(value, key, exceptions))
           else:
               result[key] = value
       return result
   ```

5. **homeassistant/components/teslemetry/strings.json**
   ```json
   {
     "calendar": {
       "tariff_content_v2": {
         "name": "Buy tariff"
       },
       "tariff_content_v2_sell_tariff": {
         "name": "Sell tariff"
       }
     }
   }
   ```

6. **tests/components/teslemetry/fixtures/site_info.json**
   - Add tariff_content_v2 data structure with seasons, energy_charges, and sell_tariff

7. **tests/components/teslemetry/test_calendar.py**
   - Include only tests for tariff calendar entities
   - Test current season detection and price period logic

**PR Title:** "Add energy price calendar platform to Teslemetry"

**PR Description:**
```
Add energy price calendar platform to Teslemetry integration

This PR adds calendar entities for energy site tariff schedules, providing:
- Buy tariff calendar showing energy purchase pricing periods
- Sell tariff calendar showing energy sell-back pricing periods

Features:
- Displays current active pricing period
- Shows seasonal pricing variations
- Handles time-of-use (TOU) periods
- Supports midnight crossing periods

Type of change: New feature
```

## PR 2: Charging Schedule Calendar

### Branch: `teslemetry-charging-schedule-calendar`

**Files to create/modify:**

1. **homeassistant/components/teslemetry/calendar.py**
   - Include helper functions: get_rrule_days, test_days_of_week, async_get_sorted_schedule_events
   - Include Schedule dataclass
   - Include only TeslemetryChargeSchedule class
   - async_setup_entry should only create TeslemetryChargeSchedule entities

2. **homeassistant/components/teslemetry/strings.json**
   ```json
   {
     "calendar": {
       "charge_schedule_data_charge_schedules": {
         "name": "Charging schedule"
       }
     }
   }
   ```

3. **tests/components/teslemetry/fixtures/vehicle_data.json**
   - Add charge_schedule_data structure with charge_schedules array

4. **tests/components/teslemetry/test_calendar.py**
   - Include only tests for charging schedule calendar entities
   - Test schedule event generation and timing logic

**PR Title:** "Add charging schedule calendar platform to Teslemetry"

**PR Description:**
```
Add charging schedule calendar platform to Teslemetry integration

This PR adds calendar entities for vehicle charging schedules, providing:
- Charging schedule calendar showing when vehicle charging is scheduled

Features:
- Displays upcoming charging events
- Supports recurring and one-time schedules
- Handles midnight-crossing charging periods
- Shows schedule location information

Type of change: New feature

Depends on: #[Energy Price Calendar PR number]
```

## PR 3: Preconditioning Schedule Calendar

### Branch: `teslemetry-preconditioning-schedule-calendar`

**Files to create/modify:**

1. **homeassistant/components/teslemetry/calendar.py**
   - Include helper functions: get_rrule_days, test_days_of_week, async_get_sorted_schedule_events (if not already present)
   - Include Schedule dataclass (if not already present)
   - Include only TeslemetryPreconditionSchedule class
   - async_setup_entry should only create TeslemetryPreconditionSchedule entities

2. **homeassistant/components/teslemetry/strings.json**
   ```json
   {
     "calendar": {
       "preconditioning_schedule_data_precondition_schedules": {
         "name": "Precondition schedule"
       }
     }
   }
   ```

3. **tests/components/teslemetry/fixtures/vehicle_data.json**
   - Add preconditioning_schedule_data structure with precondition_schedules array

4. **tests/components/teslemetry/test_calendar.py**
   - Include only tests for preconditioning schedule calendar entities
   - Test instantaneous event handling

**PR Title:** "Add preconditioning schedule calendar platform to Teslemetry"

**PR Description:**
```
Add preconditioning schedule calendar platform to Teslemetry integration

This PR adds calendar entities for vehicle preconditioning schedules, providing:
- Preconditioning schedule calendar showing when vehicle preconditioning is scheduled

Features:
- Displays upcoming preconditioning events
- Supports recurring and one-time schedules
- Shows instantaneous preconditioning events
- Shows schedule location information

Type of change: New feature

Depends on: #[Charging Schedule Calendar PR number]
```

## Implementation Order

1. **First PR: Energy Price Calendar** - Independent feature, can be implemented first
2. **Second PR: Charging Schedule Calendar** - Depends on any shared helper functions
3. **Third PR: Preconditioning Schedule Calendar** - Can reuse helper functions from PR 2

## Testing Strategy

Each PR should:
- Include comprehensive unit tests for the specific calendar type
- Test entity creation and availability
- Test event generation within date ranges
- Test edge cases (midnight crossing, one-time events, etc.)
- Include snapshot tests for entity states and events

## Code Review Focus Points

**Energy Price Calendar:**
- Season detection logic
- Price period calculation
- Midnight crossing handling

**Charging Schedule Calendar:**
- Schedule parsing and event generation
- Start/end time handling with enabled/disabled flags
- Recurring vs one-time schedule logic

**Preconditioning Schedule Calendar:**
- Instantaneous event handling
- Schedule timing accuracy
- One-time vs recurring differentiation

## Merge Strategy

1. Merge PRs in order (Energy Price → Charging → Preconditioning)
2. Each subsequent PR should be rebased on the previous merged PR
3. Update dependency comments in PR descriptions with actual PR numbers
4. Consider squashing commits in each PR for cleaner history

This approach will make each PR focused, reviewable, and maintainable while preserving all functionality from the original large PR.