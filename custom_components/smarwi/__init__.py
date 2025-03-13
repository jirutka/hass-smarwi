# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
"""Integration for Vektiva SMARWI window opener."""

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_REMOTE_ID, DOMAIN, LOGGER
from .device import SmarwiDevice

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMARWI from a config entry."""

    # Make sure MQTT integration is enabled and the client is available.
    if not await mqtt.async_wait_for_mqtt_client(hass):
        LOGGER.error("MQTT integration is not available")
        return False

    remote_id: str = entry.data[CONF_REMOTE_ID]
    entry_id: str = entry.entry_id
    hass_data: dict[str, SmarwiDevice] = hass.data.setdefault(  # pyright:ignore[reportAny]
        DOMAIN, {}
    ).setdefault(entry_id, {})

    async def device_discovery(msg: mqtt.ReceiveMessage) -> None:
        # Topic looks like ion/<remote_id>/%<device_id>/status.
        device_id = msg.topic.split("/")[2].removeprefix("%")

        # Check if this device is already known
        if device_id in hass_data:
            return

        LOGGER.info(f"Discovered new SMARWI device: {device_id}")

        hass_data[device_id] = device = SmarwiDevice(hass, entry, device_id)
        await device.async_init()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Discover SMARWI devices with the configured REMOTE ID.
    LOGGER.debug(f"Subscribing to ion/{remote_id}/+/online")
    entry.async_on_unload(
        await mqtt.async_subscribe(hass, f"ion/{remote_id}/+/online", device_discovery)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    hass_data: dict[str, SmarwiDevice] = hass.data[DOMAIN]  # pyright:ignore[reportAny]

    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del hass_data[entry.entry_id]

    return unloaded
