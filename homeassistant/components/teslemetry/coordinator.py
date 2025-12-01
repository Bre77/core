"""Teslemetry Data Coordinator."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from tesla_fleet_api.const import TeslaEnergyPeriod, VehicleDataEndpoint
from tesla_fleet_api.exceptions import (
    InvalidToken,
    SubscriptionRequired,
    TeslaFleetError,
)
from tesla_fleet_api.teslemetry import EnergySite, Vehicle

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import EnergyConverter

if TYPE_CHECKING:
    from . import TeslemetryConfigEntry

from .const import DOMAIN, ENERGY_HISTORY_FIELDS, LOGGER
from .helpers import flatten

VEHICLE_INTERVAL = timedelta(seconds=60)
VEHICLE_WAIT = timedelta(minutes=15)
ENERGY_LIVE_INTERVAL = timedelta(seconds=30)
ENERGY_INFO_INTERVAL = timedelta(seconds=30)
ENERGY_HISTORY_INTERVAL = timedelta(seconds=60)

ENDPOINTS = [
    VehicleDataEndpoint.CHARGE_STATE,
    VehicleDataEndpoint.CLIMATE_STATE,
    VehicleDataEndpoint.DRIVE_STATE,
    VehicleDataEndpoint.LOCATION_DATA,
    VehicleDataEndpoint.VEHICLE_STATE,
    VehicleDataEndpoint.VEHICLE_CONFIG,
]


class TeslemetryVehicleDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Teslemetry API."""

    config_entry: TeslemetryConfigEntry
    last_active: datetime

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TeslemetryConfigEntry,
        api: Vehicle,
        product: dict,
    ) -> None:
        """Initialize Teslemetry Vehicle Update Coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name="Teslemetry Vehicle",
        )
        if product["command_signing"] == "off":
            # Only allow automatic polling if its included
            self.update_interval = VEHICLE_INTERVAL

        self.api = api
        self.data = flatten(product)
        self.last_active = datetime.now()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update vehicle data using Teslemetry API."""

        try:
            data = (await self.api.vehicle_data(endpoints=ENDPOINTS))["response"]
        except (InvalidToken, SubscriptionRequired) as e:
            raise ConfigEntryAuthFailed from e
        except TeslaFleetError as e:
            raise UpdateFailed(e.message) from e

        return flatten(data)


class TeslemetryEnergySiteLiveCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching energy site live status from the Teslemetry API."""

    config_entry: TeslemetryConfigEntry
    updated_once: bool

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TeslemetryConfigEntry,
        api: EnergySite,
        data: dict,
    ) -> None:
        """Initialize Teslemetry Energy Site Live coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name="Teslemetry Energy Site Live",
            update_interval=ENERGY_LIVE_INTERVAL,
        )
        self.api = api

        # Convert Wall Connectors from array to dict
        data["wall_connectors"] = {
            wc["din"]: wc for wc in (data.get("wall_connectors") or [])
        }
        self.data = data

    async def _async_update_data(self) -> dict[str, Any]:
        """Update energy site data using Teslemetry API."""

        try:
            data = (await self.api.live_status())["response"]
        except (InvalidToken, SubscriptionRequired) as e:
            raise ConfigEntryAuthFailed from e
        except TeslaFleetError as e:
            raise UpdateFailed(e.message) from e

        # Convert Wall Connectors from array to dict
        data["wall_connectors"] = {
            wc["din"]: wc for wc in (data.get("wall_connectors") or [])
        }

        return data


class TeslemetryEnergySiteInfoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching energy site info from the Teslemetry API."""

    config_entry: TeslemetryConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TeslemetryConfigEntry,
        api: EnergySite,
        product: dict,
    ) -> None:
        """Initialize Teslemetry Energy Info coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name="Teslemetry Energy Site Info",
            update_interval=ENERGY_INFO_INTERVAL,
        )
        self.api = api
        self.data = product

    async def _async_update_data(self) -> dict[str, Any]:
        """Update energy site data using Teslemetry API."""

        try:
            data = (await self.api.site_info())["response"]
        except (InvalidToken, SubscriptionRequired) as e:
            raise ConfigEntryAuthFailed from e
        except TeslaFleetError as e:
            raise UpdateFailed(e.message) from e

        return flatten(data)


class TeslemetryEnergyHistoryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching energy site info from the Teslemetry API."""

    config_entry: TeslemetryConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TeslemetryConfigEntry,
        api: EnergySite,
    ) -> None:
        """Initialize Teslemetry Energy Info coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=f"Teslemetry Energy History {api.energy_site_id}",
            update_interval=ENERGY_HISTORY_INTERVAL,
        )
        self.api = api
        self.data = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Update energy site data using Teslemetry API."""

        try:
            data = (await self.api.energy_history(TeslaEnergyPeriod.DAY))["response"]
        except (InvalidToken, SubscriptionRequired) as e:
            raise ConfigEntryAuthFailed from e
        except TeslaFleetError as e:
            raise UpdateFailed(e.message) from e

        if not data or not isinstance(data.get("time_series"), list):
            raise UpdateFailed("Received invalid data")

        time_series = data.get("time_series", [])

        # Insert external statistics with historical timestamps
        await self._insert_statistics(time_series)

        # Calculate daily sums for sensor entities
        output: dict[str, Any] = dict.fromkeys(ENERGY_HISTORY_FIELDS, None)
        for period in time_series:
            for key in ENERGY_HISTORY_FIELDS:
                if key in period:
                    if output[key] is None:
                        output[key] = period[key]
                    else:
                        output[key] += period[key]

        return output

    async def _insert_statistics(self, time_series: list[dict[str, Any]]) -> None:
        """Insert energy history statistics at their actual historical timestamps."""
        if not time_series:
            return

        site_id = self.api.energy_site_id
        recorder = get_instance(self.hass)

        for key in ENERGY_HISTORY_FIELDS:
            statistic_id = f"{DOMAIN}:{site_id}_{key}"

            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=f"Tesla energy site {site_id} {key.replace('_', ' ')}",
                source=DOMAIN,
                statistic_id=statistic_id,
                unit_class=EnergyConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            )

            # Get the last recorded statistic to determine where to start
            last_stat = await recorder.async_add_executor_job(
                get_last_statistics, self.hass, 1, statistic_id, True, {"sum"}
            )

            if not last_stat:
                # First time - start from scratch
                LOGGER.debug(
                    "Inserting statistics for %s for the first time", statistic_id
                )
                last_stats_time = None
                running_sum = 0.0
            else:
                last_stats_time = last_stat[statistic_id][0]["start"]
                running_sum = cast(float, last_stat[statistic_id][0].get("sum", 0.0))

            statistics: list[StatisticData] = []

            for period in time_series:
                timestamp_str = period.get("timestamp")
                if not timestamp_str:
                    continue

                start = dt_util.parse_datetime(timestamp_str)
                if start is None:
                    continue

                # Skip if we already have this statistic
                if last_stats_time is not None and start.timestamp() <= last_stats_time:
                    continue

                value = period.get(key)
                if value is None:
                    continue

                state = float(value)
                running_sum += state

                statistics.append(
                    StatisticData(start=start, state=state, sum=running_sum)
                )

            if statistics:
                LOGGER.debug(
                    "Adding %s statistics for %s",
                    len(statistics),
                    statistic_id,
                )
                async_add_external_statistics(self.hass, metadata, statistics)
