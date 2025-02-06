"""Platform for sensor integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import itertools
import json
import logging
import statistics

import brotli
from homeassistant_historical_sensor import (
    HistoricalSensor,
    HistoricalState,
    PollUpdateMixin,
)
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(hours=24)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> bool:
    """Set up the Thames Water sensor platform."""
    username = entry.data["username"]
    password = entry.data["password"]
    selenium_url = entry.data["selenium_url"]
    account_number = entry.data["account_number"]
    meter_id = entry.data["meter_id"]

    async_add_entities(
        [
            ThamesWaterUsageSensor(
                hass, username, password, account_number, meter_id, selenium_url
            )
        ],
        update_before_add=True,
    )
    return True


class ThamesWaterUsageSensor(PollUpdateMixin, HistoricalSensor, SensorEntity):
    """Representation of a Thames Water usage sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        account_number: str,
        meter_id: str,
        selenium_url: str,
    ) -> None:
        """Initialize the sensor."""
        self._attr_has_entity_name = True
        self._attr_name = "Thames Water Usage"

        self._attr_unique_id = f"thames_water_usage_{meter_id}"

        self._attr_entity_registry_enabled_default = True
        self._attr_state = None

        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS

        self.UPDATE_INTERVAL = SCAN_INTERVAL

        self.hass = hass
        self.username = username
        self.password = password
        self.account_number = account_number
        self.meter_id = meter_id
        self.selenium_url = selenium_url
        self.initialised = False
        self.cookies_dict = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="Thames Water",
            model="Water Meter",
            name="Thames Water Meter",
        )

    async def async_update_historical(self):
        """Fetch new data for the sensor."""
        try:
            # Determine the date range
            end_date = datetime.now() - timedelta(days=3)
            if not self.initialised:
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=3)

            # Fetch data for each day in the date range
            current_date = start_date
            hist_states = []
            while current_date <= end_date:
                year = current_date.year
                month = current_date.month
                day = current_date.day

                # Run the blocking Selenium operation in a separate thread
                data = await self.hass.async_add_executor_job(
                    self._fetch_data_with_selenium,
                    year,
                    month,
                    day,
                    self.account_number,
                    self.meter_id,
                )

                # Process the lines of data
                lines = data.get("Lines", [])
                for line in lines:
                    time = line.get("Label")
                    usage = line.get("Usage")
                    hour, minute = map(int, time.split(":"))
                    naive_datetime = datetime(year, month, day, hour, minute)
                    hist_states.append(
                        HistoricalState(
                            state=usage,
                            dt=dt_util.as_local(naive_datetime + timedelta(minutes=1)),
                        )
                    )

                current_date += timedelta(days=1)

            self.initialised = True
            self._attr_historical_states = hist_states

        except Exception as e:
            _LOGGER.error("Error during Selenium operation: %s", e)

    @property
    def statistic_id(self) -> str:
        return self.entity_id

    def get_statistic_metadata(self) -> StatisticMetaData:
        #
        # Add sum and mean to base statistics metadata
        # Important: HistoricalSensor.get_statistic_metadata returns an
        # internal source by default.
        #
        meta = super().get_statistic_metadata()
        meta["has_sum"] = True
        meta["has_mean"] = True

        return meta

    async def async_calculate_statistic_data(
        self, hist_states: list[HistoricalState], *, latest: dict | None = None
    ) -> list[StatisticData]:
        #
        # Group historical states by hour
        # Calculate sum, mean, etc...
        #

        accumulated = latest["sum"] if latest else 0

        def hour_block_for_hist_state(hist_state: HistoricalState) -> datetime:
            # XX:00:00 states belongs to previous hour block
            if hist_state.dt.minute == 0 and hist_state.dt.second == 0:
                dt = hist_state.dt - timedelta(hours=1)
                return dt.replace(minute=0, second=0, microsecond=0)
            return hist_state.dt.replace(minute=0, second=0, microsecond=0)

        ret = []
        for dt, collection_it in itertools.groupby(
            hist_states, key=hour_block_for_hist_state
        ):
            collection = list(collection_it)
            mean = statistics.mean([x.state for x in collection])
            partial_sum = sum([x.state for x in collection])
            accumulated = accumulated + partial_sum

            ret.append(
                StatisticData(
                    start=dt,
                    state=partial_sum,
                    mean=mean,
                    sum=accumulated,
                )
            )

        return ret

    def _fetch_data_with_selenium(
        self, year: int, month: int, day: int, account_number: str, meter_id: str
    ) -> dict:
        """Fetch data using Selenium in a blocking manner."""
        driver = None
        try:
            if not self.cookies_dict:
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # Run in headless mode
                chrome_options.add_argument(
                    "--no-sandbox"
                )  # Required for some environments
                chrome_options.add_argument(
                    "--disable-dev-shm-usage"
                )  # Overcome limited resource problems

                # Connect to the Selenium server
                driver = webdriver.Remote(
                    command_executor=self.selenium_url, options=chrome_options
                )

                # Navigate to the login page
                driver.get("https://www.thameswater.co.uk/login")

                # Find and fill the email and password fields
                email_element = driver.find_element(By.ID, "email")
                password_element = driver.find_element(By.ID, "password")
                submit_element = driver.find_element(By.ID, "next")

                email_element.send_keys(self.username)
                password_element.send_keys(self.password)

                # Submit the form
                submit_element.click()

                # Wait for specific text to appear on the page
                WebDriverWait(driver, 30).until(
                    EC.text_to_be_present_in_element(
                        (By.TAG_NAME, "body"), account_number
                    )
                )

                driver.get(
                    f"https://myaccount.thameswater.co.uk/mydashboard/my-meters-usage?contractAccountNumber={account_number}"
                )

                # Wait for specific text to appear on the page
                WebDriverWait(driver, 30).until(
                    EC.text_to_be_present_in_element(
                        (By.TAG_NAME, "body"), account_number
                    )
                )

                # Retrieve cookies after successful login
                cookies = driver.get_cookies()
                _LOGGER.info("Cookies after login: %s", cookies)

                # Prepare cookies for the requests library
                self.cookies_dict = {
                    cookie["name"]: cookie["value"] for cookie in cookies
                }

            # Make a GET request with cookies and referer
            url = "https://myaccount.thameswater.co.uk/ajax/waterMeter/getSmartWaterMeterConsumptions"
            params = {
                "meter": meter_id,
                "startDate": day,
                "startMonth": month,
                "startYear": year,
                "endDate": day,
                "endMonth": month,
                "endYear": year,
                "granularity": "H",
                "isForC4C": "false",
            }
            headers = {
                "referer": "https://myaccount.thameswater.co.uk/mydashboard/my-meters-usage",
                "x-requested-with": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            response = requests.get(
                url, params=params, cookies=self.cookies_dict, headers=headers
            )
            _LOGGER.info("Response headers: %s", response.headers)

            # Check if the response is Brotli compressed
            decompressed_data = ""
            try:
                if response.headers.get("Content-Encoding") == "br":
                    decompressed_data = brotli.decompress(response.content)
                else:
                    decompressed_data = response.content
            except Exception as e:
                # Directly decode the response content
                decompressed_data = response.content

            # Decode the decompressed data
            response_text = decompressed_data.decode("utf-8")
            _LOGGER.info("Decompressed response: %s", response_text)

            # Parse the JSON response
            data = json.loads(response_text)

            # Check for errors in the response
            if data.get("IsError"):
                _LOGGER.error("Error in response: %s", data)
                return {}

            # Check if data is available
            if not data.get("IsDataAvailable"):
                _LOGGER.warning("No data available in response.")
                return {}

            return data

        finally:
            if driver is not None:
                driver.quit()
