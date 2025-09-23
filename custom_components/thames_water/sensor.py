"""Water meter sensor implementation."""

from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from typing import List, Optional

from .entity import ThamesWaterDevice
from .number import CostConfiguration, WaterCostCalculator

_LOGGER = logging.getLogger(__name__)


@dataclass
class WaterMeterReading:
    """Represents a single water meter reading."""
    timestamp: datetime
    usage: float  # Liters
    cumulative: float  # Total liters
    estimated: bool = False


class WaterMeterStats:
    """Statistics calculator for water meter readings."""

    def __init__(self, cost_config: Optional[CostConfiguration] = None):
        """Initialize the statistics calculator."""
        self.readings: List[WaterMeterReading] = []
        self.cost_calculator = WaterCostCalculator(cost_config) if cost_config else None

    def add_reading(self, reading: WaterMeterReading) -> None:
        """Add a new reading."""
        self.readings.append(reading)
        self.readings.sort(key=lambda x: x.timestamp)

    def get_usage_in_range(
        self, start: datetime, end: datetime
    ) -> List[WaterMeterReading]:
        """Get readings within a date range."""
        return [
            r for r in self.readings
            if start <= r.timestamp <= end
        ]

    def get_total_usage(self) -> float:
        """Get total water usage in liters."""
        return sum(r.usage for r in self.readings)

    def get_total_cost(self) -> Optional[float]:
        """Get total cost if cost calculator is configured."""
        if not self.cost_calculator:
            return None
        return self.cost_calculator.calculate_cost(self.get_total_usage())


class WaterMeterSensor(ThamesWaterDevice):
    """Sensor for reading water meter data."""

    def __init__(
        self,
        meter_id: str,
        account_number: str,
        cost_config: Optional[CostConfiguration] = None,
        update_interval: timedelta = timedelta(hours=1),
    ):
        """Initialize the water meter sensor."""
        super().__init__(meter_id, account_number)
        self.stats = WaterMeterStats(cost_config)
        self.update_interval = update_interval
        self.last_update: Optional[datetime] = None
        self._current_reading: Optional[WaterMeterReading] = None

    def update(self) -> None:
        """Update sensor state."""
        current_time = datetime.now()
        if (
            self.last_update
            and current_time - self.last_update < self.update_interval
        ):
            return

        # This would be where you fetch new data from the meter
        # For now we'll just log that we would update
        _LOGGER.debug(
            "Would update meter %s for account %s",
            self.meter_id,
            self.account_number
        )
        self.last_update = current_time

    @property
    def current_usage(self) -> Optional[float]:
        """Get the current water usage in liters."""
        return self._current_reading.usage if self._current_reading else None

    @property
    def current_cost(self) -> Optional[float]:
        """Get the current cost if cost calculator is configured."""
        if not self._current_reading or not self.stats.cost_calculator:
            return None
        return self.stats.cost_calculator.calculate_cost(self._current_reading.usage)
