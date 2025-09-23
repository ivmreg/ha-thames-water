"""Cost configuration for Thames Water."""

from dataclasses import dataclass
from typing import Callable, Optional

from .entity import ThamesWaterDevice


@dataclass
class CostConfiguration:
    """Configuration for water cost calculation."""
    liter_cost: float = 0.0030682
    currency: str = "GBP"
    min_value: float = 0.00005
    max_value: float = 1.0
    step: float = 0.00005

    def __post_init__(self):
        """Validate the configuration."""
        if not self.min_value <= self.liter_cost <= self.max_value:
            raise ValueError(
                f"Liter cost must be between {self.min_value} and {self.max_value}"
            )


class WaterCostCalculator:
    """Calculator for water costs."""

    def __init__(
        self,
        config: CostConfiguration,
        on_update: Optional[Callable[[float], None]] = None
    ):
        """Initialize the cost calculator."""
        self.config = config
        self._on_update = on_update

    def calculate_cost(self, volume_liters: float) -> float:
        """Calculate cost for given volume of water."""
        return volume_liters * self.config.liter_cost

    def update_liter_cost(self, new_cost: float) -> None:
        """Update the cost per liter."""
        if not self.config.min_value <= new_cost <= self.config.max_value:
            raise ValueError(
                f"Liter cost must be between {self.config.min_value} and {self.config.max_value}"
            )
        self.config.liter_cost = new_cost
        if self._on_update:
            self._on_update(new_cost)
