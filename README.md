# Thames Water Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/ar770)

# Home Assistant Integration for Thames Water Consumption Data

This Home Assistant integration retrieves water consumption data from Thames Water using their API. It allows you to monitor your water usage without needing additional devices, directly from your Home Assistant setup.

You probably need a Thames Water Smart meter.
The water consumption data provided by this integration is delayed by approximately 3 days. This is a characteristic of the Thames Water data system and cannot be altered in this integration.

The integration logs into the thames water website using your credentials to get the browser cookies.

With these cookies it then calls the https://myaccount.thameswater.co.uk/ajax/waterMeter/getSmartWaterMeterConsumptions API to retrieve the usage.

The integration was created recently so it may contain bugs. Proceed with caution!

## Installation

### Installation through HACS

1. Install the custom component using the Home Assistant Community Store (HACS) by adding the Custom Repository:
https://github.com/ale770/ha-thames-water
2. In the HACS panel, select Thames Water from the repository list and select the DOWNLOAD button.
3. Restart HA
4. Go to Settings > Devices & Services > Add Integration and select Thames Water.

### Manual installation

Copy the `custom_components/thames_water/` directory and all of its files to your `config/custom_components/` directory.

## Configuration

Once installed, restart Home Assistant:

[![Open your Home Assistant instance and show the system dashboard.](https://my.home-assistant.io/badges/system_dashboard.svg)](https://my.home-assistant.io/redirect/system_dashboard/)

Then, add the integration:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=thames_water)


<details>
  <summary>Manually add the Integration</summary>
  Visit the <i>Integrations</i> section in Home Assistant and click the <i>Add</i> button in the bottom right corner. Search for <code>Thames Water</code> and input your credentials. <b>You may need to clear your browser cache before the integration appears in the list.</b>
</details>

## Sensors

The integration will automatically set up the water usage sensor (L).

It updates every day between 12-13pm.

## Energy Management

The sensor created integrates directly into Home Assistant's [Home Energy Management](https://www.home-assistant.io/docs/energy/).

[![Open your Home Assistant instance and show your Energy configuration panel.](https://my.home-assistant.io/badges/config_energy.svg)](https://my.home-assistant.io/redirect/config_energy/)

![Dashboard](./dashboard.png)


