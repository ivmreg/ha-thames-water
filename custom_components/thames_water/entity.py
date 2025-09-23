"""Base class for Thames Water meters and readings."""

from abc import ABC, abstractmethod

class ThamesWaterDevice(ABC):
    """Base class for Thames Water devices."""

    def __init__(self, meter_id: str, account_number: str):
        """Initialize the device."""
        self.meter_id = meter_id
        self.account_number = account_number

    @property
    def device_info(self):
        """Return device information."""
        return {
            "id": self.meter_id,
            "manufacturer": "Thames Water",
            "model": "Smart Water Meter",
            "name": f"Thames Water Meter {self.meter_id}",
            "account": self.account_number
        }

    @abstractmethod
    def update(self):
        """Update the device state."""
        pass
