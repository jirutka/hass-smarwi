# SMARWI Integration
<img src="https://raw.githubusercontent.com/jirutka/hass-smarwi/master/images/logo.png" width="250px" align="right">

[![GitHub Release][releases-shield]][releases]

Home Assistant integration for Vektiva [SMARWI][smarwi-website] window opener (actuator).

It uses a local MQTT broker, no “cloud” service is required.


## Installation

### Using Home Assistant Community Store (HACS)

1. Ensure that [HACS] is installed.
1. Go to **HACS > Integrations**.
1. Click on the hamburger menu in the top right corner, select **Custom repositories**, and fill in:
   - Repository: `https://github.com/jirutka/hass-smarwi/`
   - Category: Integration
1. Click on the **⊕ Explore & download repositories** button in the bottom right corner, then search for and select **SMARWI**.
1. Click on the **Download** button in the bottom right corner.
1. Restart Home Assistant.

**TIP:** You can skip steps 2–4 by opening:

[![Add jirutka/hass-smarwi repository to your Home Assistant instance][my-hacs-repo-img]][my-hacs-repo]


### Manually

1. Download `smarwi.zip` from the [latest release][latest-release].
1. Unpack `smarwi.zip` and copy the `custom_components/smarwi` directory into the `custom_components` directory of your Home Assistant installation.
1. Restart Home Assistant.


## Configuration

### 1. Set up MQTT broker

1. Set up your MQTT broker, if you don’t already have one (see [Choose an MQTT broker][choose-mqtt-broker] if you’re unsure).
1. [Add the MQTT integration][my-hass-mqtt] to your Home Assistant instance (see [mqtt-integration][documentation]).


### 2. Prepare SMARWI devices

For each SMARWI device:

1. Connect to your SMARWI device and open its web interface in the browser (see section 6.1.2 in the [SMARWI manual][smarwi-manual]).
1. Go to **Settings > Advanced**, fill domain name or IP address of your local MQTT broker (see above), and click **Save**.
1. Go to **Basic** and fill in the following:
   - **Device name** – this will be used in Home Assistant to identify each SMARWI device;
   - **Remote ID** – choose any name (no registration needed), but the same for all your SMARWI devices, it will be used as a prefix for MQTT topics (`ion/<remote-id>/%<device-id>/+`);
   - **Remote Key** – leave empty;
   - **Wifi Mode** – change to `Client`;
   - **Select Wifi network** – select SSID of your Wi-Fi network;
   - **Wifi Password** – password for your Wi-Fi network (max 32 characters).
1. Click on **Save**.

SMARWI should be connected to your Wi-Fi network and MQTT broker now.


### 3. Add integration

1. Browse to your Home Assistant instance.
1. Go to **Settings > Devices & Services**.
1. In the bottom right corner, select the **⊕ Add Integration** button.
1. From the list, select **SMARWI**.
1. Fill in the **Remote ID** that you choose for your SMARWI devices (see above).

The integration should now automatically detect all your SMARWI devices.

**TIP:** You can skip steps 1–4 by opening:

[![Add SMARWI integration to your Home Assistant instance][my-hass-config-start-img]][my-hass-smarwi]


## Entities

The integration will create the following entities for each discovered SMARWI device.

| Name                | Platform      | Category   | Description
| ------------------- | ------------- | ---------- | --------------------------------------------------------------------------|
| cover               | cover         |            | Control the window tilt position (open, close, stop, set position). |
| ridge_fix           | switch        |            | Fix or release the ridge. |
| ridge_inside        | binary_sensor | diagnostic | Shows if the ridge is inside the device (i.e. it’s operational). |
| rssi                | sensor        | diagnostic | Monitor WiFi signal strength (disabled by default). |
| calibrated_distance | number        | config     | Set calibrated distance (finetune setting, disabled by default). |
| closed_hold_power   | number        | config     | Set closed holding power (finetune setting). |
| closed_position     | number        | config     | Set window closed position finetune (finetune setting). |
| frame_power         | number        | config     | Set near frame power (finetune setting). |
| frame_speed         | number        | config     | Set near frame speed (finetune setting). |
| lock_err_trigger    | number        | config     | Set window locked error trigger (finetune setting). |
| max_open_position   | number        | config     | Set maximum open position (finetune setting). |
| move_power          | number        | config     | Set movement power (finetune setting). |
| move_speed          | number        | config     | Set movement speed (finetune setting). |
| opened_hold_power   | number        | config     | Set opened holding power (finetune setting). |


## Screenshots

<img src="https://raw.githubusercontent.com/jirutka/hass-smarwi/master/images/screenshot-device.png" width="500px" align="left" alt="Screenshot of the device dashboard">

<img src="https://raw.githubusercontent.com/jirutka/hass-smarwi/master/images/screenshot-cover-position.png" width="300px" alt="Screenshot of the cover control in position mode">

<img src="https://raw.githubusercontent.com/jirutka/hass-smarwi/master/images/screenshot-cover-buttons.png" width="300px" alt="Screenshot of the cover control in button mode">


## Resources

- [SMARWI product website][smarwi-website]
- [SMARWI user manual][smarwi-manual]
- [SMARWI API documentation][smarwi-api-doc]


## License

This project is licensed under the [MIT License].


[releases]: https://github.com/jirutka/hass-smarwi/releases
[latest-release]: https://github.com/jirutka/hass-smarwi/releases/latest
[releases-shield]: https://img.shields.io/github/release/jirutka/hass-smarwi.svg?style=flat-square
[HACS]: https://hacs.xyz/
[smarwi-website]: https://vektiva.com/index.php/en/
[smarwi-manual]: https://vektiva.com/downloads/SMARWI_manual_EN.pdf
[smarwi-api-doc]: https://vektiva.gitlab.io/vektivadocs/en/api/index.html
[my-hass-mqtt]: https://my.home-assistant.io/redirect/config_flow_start/?domain=mqtt
[my-hass-smarwi]: https://my.home-assistant.io/redirect/config_flow_start/?domain=smarwi
[my-hass-config-start-img]: https://my.home-assistant.io/badges/config_flow_start.svg
[my-hacs-repo]: https://my.home-assistant.io/redirect/hacs_repository/?owner=jirutka&repository=hass-smarwi&category=Integration
[my-hacs-repo-img]: https://my.home-assistant.io/badges/hacs_repository.svg
[choose-mqtt-broker]: https://www.home-assistant.io/integrations/mqtt/#choose-an-mqtt-broker
[mqtt-integration]: https://www.home-assistant.io/integrations/mqtt/
[MIT License]: https://opensource.org/license/MIT
