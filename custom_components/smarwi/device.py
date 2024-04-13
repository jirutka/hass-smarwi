# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>

from __future__ import annotations

from enum import IntEnum, StrEnum
from functools import cached_property
import logging
import socket
import struct
from typing import TYPE_CHECKING, Any  # pyright:ignore[reportAny]
from typing_extensions import override

import aiohttp
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_REMOTE_ID, DOMAIN

if TYPE_CHECKING:
    from functools import cached_property
else:
    from homeassistant.backports.functools import cached_property

__all__ = ["FinetuneSetting", "SmarwiDevice", "StateCode"]

_LOGGER = logging.getLogger(__name__)


class SmarwiDeviceProp(StrEnum):
    """Updatable properties of SmarwiDevice."""

    # status properties
    NAME = "cid"
    RIDGE_FIXED = "fix"
    FW_VERSION = "fw"
    IP_ADDRESS = "ip"
    CLOSED = "pos"
    RIDGE_INSIDE = "ro"
    RSSI = "rssi"
    STATE_CODE = "s"
    # others
    AVAILABLE = "available"
    FINETUNE_SETTINGS = "finetune_settings"

    @override
    def __hash__(self) -> int:
        return hash(self.name)


class FinetuneSetting(StrEnum):
    """SMARWI finetune setting keys."""

    MAX_OPEN_POSITION = "vpct"  # Maximum open position
    MOVE_SPEED = "ospd"  # Movement speed
    FRAME_SPEED = "ofspd"  # Near frame speed
    MOVE_POWER = "orpwr"  # Movement power
    FRAME_POWER = "ofpwr"  # Near frame power
    CLOSED_HOLD_POWER = "ohcpwr"  # Closed holding power
    OPENED_HOLD_POWER = "ohopwr"  # Opened holding power
    CLOSED_POSITION = "hdist"  # Window closed position finetune
    LOCK_ERR_TRIGGER = "lwid"  # "Window locked" error trigger
    CALIBRATED_DISTANCE = "cfdist"  # Calibrated distance


class StateCode(IntEnum):
    """SMARWI state codes."""

    CALIBRATION = -1  # Calibration in progress
    UNKNOWN = 0  # Fallback for unknown code
    ERR_WINDOW_LOCKED = 10  # Window is locked to frame
    ERR_MOVE_TIMEOUT = 20  # Operation move to frame sensor from ventilation timeout
    ERR_WINDOW_HORIZ = 30  # Indicates, that window is opened in horizontal position
    OPENING_START = 200  # Moving to frame sensor position within opening phase.
    OPENING = 210  # Opening phase lasts until target ventilation position is reached
    REOPEN_START = 212  # Reopen in executed when open operation is invoked while window position is between frame sensor and ventilation distance
    REOPEN_PHASE = 214  # Window reached frame sensor
    REOPEN_FINAL = 216  # Final phase of reopen operation.. window moved to target ventilation position
    CLOSING_START = 220  # Moving to frame sensor position within closing phase
    CLOSING = 230  # Closing phase lasts until target closed position is reached
    CLOSING_NICE = 231  # Closing step by step until obstacle detected?
    RECLOSE_START = 232  # Re-closing starts when close operation in invoked while window position is between frame and frame sensor
    RECLOSE_PHASE = 234  # Window moved after frame sensor
    IDLE = 250

    @override
    @classmethod
    def _missing_(cls, value: object):
        return cls.UNKNOWN

    def is_error(self) -> bool:
        """Return True if the state indicate an error (or in calibration)."""
        return self.value < 200

    def is_idle(self) -> bool:
        """Return True if the window is in idle."""
        return self == StateCode.IDLE

    def is_moving(self) -> bool:
        """Return True if the window is moving."""
        return 199 < self.value < 250

    def is_near_frame(self) -> bool:
        """Return True if the window is between the frame and the frame sensor."""
        # TODO: add more?
        return self in (
            StateCode.OPENING_START,
            StateCode.REOPEN_PHASE,
            StateCode.CLOSING,
            StateCode.CLOSING_NICE,
        )


class SmarwiDevice:
    """This class handles communication with a single SMARWI device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize. Run .async_connect() afterwards."""
        super().__init__()
        config: dict[str, Any] = entry.data  # pyright:ignore[reportAny]

        self._hass = hass
        self._config_entry = entry
        self._id = device_id

        self._remote_id: str = config[CONF_REMOTE_ID]
        self._base_topic = f"ion/{self._remote_id}/%{device_id}"
        self._available = False
        self._status: dict[SmarwiDeviceProp, str] = {}
        self._finetune_settings = FinetuneSettings(self)

    @cached_property
    def id(self) -> str:
        """Return device ID."""
        return self._id

    @cached_property
    def finetune_settings(self) -> FinetuneSettings:
        """Return Finetune settings."""
        return self._finetune_settings

    @cached_property
    def signal_update(self) -> str:
        """Device specific event to signal a change in the status properties or availability."""
        return f"{DOMAIN}_{self.id}_update"

    @property
    def available(self) -> bool:
        """Return True if the device is available (online), otherwise False."""
        return self._available

    @property
    def closed(self) -> bool | None:
        """Return True if the window is open, False if closed."""
        if SmarwiDeviceProp.CLOSED in self._status:
            return self._status[SmarwiDeviceProp.CLOSED] == "c"

    @property
    def fw_version(self) -> str | None:
        """Return the firmware version of the device."""
        return self._status.get(SmarwiDeviceProp.FW_VERSION)

    @property
    def ip_address(self) -> str | None:
        """Return the IPv4 address of the device."""
        if SmarwiDeviceProp.IP_ADDRESS in self._status:
            return parse_ipv4(int(self._status[SmarwiDeviceProp.IP_ADDRESS]))

    @property
    def name(self) -> str | None:
        """Return the device name configured in the SMARWI settings."""
        return self._status.get(SmarwiDeviceProp.NAME)

    @property
    def ridge_fixed(self) -> bool:
        """Return True if the ridge is fixed, i.e. the window cannot be moved by hand."""
        return self._status.get(SmarwiDeviceProp.RIDGE_FIXED) == "1"

    @property
    def ridge_inside(self) -> bool:
        """Return True if the ridge is inside the device, i.e. it can be controlled."""
        return self._status.get(SmarwiDeviceProp.RIDGE_INSIDE) == "0"

    @property
    def rssi(self) -> int | None:
        """Return the WiFi signal strength."""
        if SmarwiDeviceProp.RSSI in self._status:
            return int(self._status[SmarwiDeviceProp.RSSI])

    @property
    def state_code(self) -> StateCode:
        """Return the SMARWI state code (parameter "s")."""
        return StateCode(int(self._status.get(SmarwiDeviceProp.STATE_CODE) or 0))

    async def async_init(self) -> None:
        """Connect to the device via MQTT."""

        async def handle_status_message(msg: mqtt.ReceiveMessage) -> None:
            status = decode_keyval(msg.payload)  # pyright:ignore[reportAny]
            status = {
                SmarwiDeviceProp(k): v for k, v in status if k in list(SmarwiDeviceProp)
            }
            changed_props = {
                name
                for name in SmarwiDeviceProp
                if self._status.get(name) != status.get(name)
            }
            self._status = status
            _LOGGER.debug(
                f"Received message from {self._base_topic}/status:\n{msg.payload}\nChanged properties: {[e.name for e in changed_props]}"  # pyright:ignore[reportAny]
            )
            if changed_props & {
                SmarwiDeviceProp.NAME,
                SmarwiDeviceProp.IP_ADDRESS,
                SmarwiDeviceProp.FW_VERSION,
            }:
                await self._async_update_device_registry()
            if SmarwiDeviceProp.IP_ADDRESS in changed_props:
                await self._finetune_settings.async_update()

            async_dispatcher_send(self._hass, self.signal_update, changed_props)

        async def handle_online_message(msg: mqtt.ReceiveMessage) -> None:
            _LOGGER.debug(
                f"Received message from {self._base_topic}/online: {msg.payload}"  # pyright:ignore[reportAny]
            )
            available: bool = msg.payload == "1"  # pyright:ignore[reportAny]
            if available != self._available:
                _LOGGER.info(
                    f"[{self.name}] SMARWI {self.id} become {'available' if available else 'unavailable'}"
                )
                self._available = available
                async_dispatcher_send(
                    self._hass, self.signal_update, {SmarwiDeviceProp.AVAILABLE}
                )

        self._config_entry.async_on_unload(
            await mqtt.async_subscribe(
                self._hass,
                f"{self._base_topic}/status",
                handle_status_message,
            )
        )
        self._config_entry.async_on_unload(
            await mqtt.async_subscribe(
                self._hass,
                f"{self._base_topic}/online",
                handle_online_message,
            )
        )

    async def async_open(self, position: int = 100) -> None:
        """Open the window; position is between 0 and 100 %."""
        if position > 1:
            _LOGGER.info(f"[{self.name}] Opening window")
            await self._async_mqtt_command(f"open;{position}")
        else:
            await self.async_close()

    async def async_close(self) -> None:
        """Close the window."""
        _LOGGER.info(f"[{self.name}] Closing window")
        await self._async_mqtt_command("close")

    async def async_stop(self) -> None:
        """Stop the movement action if moving."""
        # If the motor is not moving, "stop" releases the ridge.
        if self.state_code.is_moving():
            _LOGGER.info(f"[{self.name}] Stopping movement of window")
            await self._async_mqtt_command("stop")

    async def async_toggle_ridge_fixed(self, state: bool) -> None:
        """Fix (True) or release (False) the ridge."""
        if state:
            if not self.ridge_fixed:
                _LOGGER.info(f"[{self.name}] Fixing ridge")
                await self._async_mqtt_command("stop")
        else:
            # If the motor is moving, "stop" stops it.
            if self.ridge_fixed and self.state_code.is_idle():
                _LOGGER.info(f"[{self.name}] Releasing ridge")
                await self._async_mqtt_command("stop")

    async def _async_mqtt_command(self, payload: str) -> None:
        _LOGGER.debug(f"Sending message to {self._base_topic}/cmd: {payload}")
        await mqtt.async_publish(self._hass, f"{self._base_topic}/cmd", payload)

    async def _async_update_device_registry(self):
        dev_registry = dr.async_get(self._hass)

        if dev := dev_registry.async_get_device(identifiers={(DOMAIN, self.id)}):
            _LOGGER.debug(f"Updating SMARWI {self.id} in device registry")
            dev_registry.async_update_device(
                dev.id,
                configuration_url=f"http://{self.ip_address}",
                name=self.name,
                sw_version=self.fw_version,
            )  # pyright:ignore[reportUnusedCallResult]


class FinetuneSettings:
    def __init__(self, device: SmarwiDevice) -> None:
        super().__init__()
        self._device = device
        self._data: dict[str, int] = {}

    def get(self, key: FinetuneSetting) -> int | None:
        return self._data.get(key.value)

    async def async_set(self, key: FinetuneSetting, value: int) -> None:
        if not self._device.ip_address:
            return
        data = self._data.copy()
        data[key.value] = value
        await http_post_data(self._device.ip_address, "scfa", encode_keyval(data))
        self._data = data  # TODO: race condition?

        await self.async_update()

    async def async_update(self) -> None:
        """Update Finetune settings from SMARWI via HTTP."""
        assert self._device.ip_address is not None, "ip_address is not known yet"

        data = await http_get(self._device.ip_address, "lcfa")
        self._data = {
            k: int(v)
            for k, v in decode_keyval(data).items()
            if k != "cvdist"  # cvdist is ready-only
        }
        async_dispatcher_send(
            self._device._hass,  # pyright:ignore[reportPrivateUsage]
            self._device.signal_update,
            {SmarwiDeviceProp.FINETUNE_SETTINGS},
        )


def parse_ipv4(packed_ip: int) -> str:
    """Parse IPv4 address represented by 32bit number in Little Endian."""
    return socket.inet_ntoa(struct.pack("<L", packed_ip))


def decode_keyval(payload: str) -> dict[str, str]:
    """Parse key:value pairs separated by newlines."""
    return dict(line.split(":", 1) for line in payload.splitlines())


def encode_keyval(data: dict[str, Any]) -> str:
    """Encode the given dict as key:value pairs separated by newlines."""
    return "\n".join(f"{k}:{v}" for k, v in data.items())  # pyright:ignore[reportAny]


async def http_get(host: str, path: str) -> str:
    """Send HTTP GET request and return the response body."""
    _LOGGER.debug(f"Sending GET http://{host}/{path}")
    async with (
        aiohttp.ClientSession(raise_for_status=True) as http,
        http.get(f"http://{host}/{path}") as resp,
    ):
        data = await resp.text()
        _LOGGER.debug(
            f"Received response for GET http://{host}/{path}: HTTP {resp.status}\n{data}"
        )
        return data


async def http_post_data(host: str, path: str, data: str) -> None:
    """Send HTTP POST request with multipart data as expected by SWARMI."""
    with aiohttp.MultipartWriter("form-data") as mpwriter:
        mpwriter.append(data.encode("ascii")).set_content_disposition(
            "form-data", name="data", filename="/afile"
        )
        _LOGGER.debug(f"POST http://{host}/{path}:\n{data}")
        async with aiohttp.ClientSession(raise_for_status=True) as http:
            await http.post(f"http://{host}/{path}", data=mpwriter)  # pyright:ignore[reportUnusedCallResult]
