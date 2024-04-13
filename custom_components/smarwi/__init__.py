# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
"""The Vektiva SMARWI integration."""

from datetime import timedelta
import logging
from typing import Any, cast  # type:ignore[Any]

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_REMOTE_ID, DOMAIN, SIGNAL_DISCOVERY_NEW
from .device import SmarwiDevice

_LOGGER = logging.getLogger(__name__)

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
        _LOGGER.error("MQTT integration is not available")
        return False

    remote_id: str = entry.data[CONF_REMOTE_ID]  # pyright:ignore[reportAny]
    entry_id: str = entry.entry_id  # pyright:ignore[reportAny]
    hass_data: dict[str, SmarwiDevice] = hass.data.setdefault(  # pyright:ignore[reportAny]
        DOMAIN, {}
    ).setdefault(entry_id, {})

    async def device_discovery(msg: mqtt.ReceiveMessage) -> None:
        # Topic looks like ion/<remote_id>/%<device_id>/status.
        device_id = msg.topic.split("/")[2].removeprefix("%")

        # Check if this device is already known
        if device_id in hass_data:
            return

        _LOGGER.info(f"Discovered new SMARWI device: {device_id}")

        hass_data[device_id] = device = SmarwiDevice(
            hass, entry, device_id, settings_ttl=timedelta(hours=1)
        )
        await device.async_init()

        async_dispatcher_send(hass, SIGNAL_DISCOVERY_NEW, entry_id, device_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Discover SMARWI devices with the configured REMOTE ID.
    _LOGGER.debug(f"Subscribing to ion/{remote_id}/+/online")
    entry.async_on_unload(
        await mqtt.async_subscribe(hass, f"ion/{remote_id}/+/online", device_discovery)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    hass_data = cast(dict[str, Any], hass.data[DOMAIN])  # pyright:ignore[reportAny]

    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        del hass_data[cast(str, entry.entry_id)]  # pyright:ignore[reportAny]

    return unloaded
