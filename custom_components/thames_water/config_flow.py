"""Configuration handling for Thames Water client."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ThamesWaterConfig:
    """Configuration for Thames Water client."""
    username: str
    password: str
    account_number: str
    meter_id: str
    liter_cost: float = 0.0030682
    fetch_hours: Optional[List[int]] = None

    def __post_init__(self):
        """Post initialization validation."""
        if self.fetch_hours is None:
            self.fetch_hours = [15, 23]
        self.validate()

    def validate(self) -> None:
        """Validate configuration values."""
        if not isinstance(self.liter_cost, float) or not (0.00005 <= self.liter_cost <= 1.0):
            raise ValueError("Liter cost must be between 0.00005 and 1.0")

        if self.fetch_hours is not None:
            if not all(isinstance(h, int) and 0 <= h <= 23 for h in self.fetch_hours):
                raise ValueError("Fetch hours must be integers between 0 and 23")
