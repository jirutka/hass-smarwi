# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
"""Support for SMARWI cover entity."""

import logging
from typing import Any  # pyright:ignore[reportAny]
from typing_extensions import override

from homeassistant.components.cover import (
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NEAR_FRAME_POSITION, SIGNAL_DISCOVERY_NEW
from .device import SmarwiDeviceProp, SmarwiDevice
from .entity import SmarwiEntity


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SMARWI window cover entities."""
    hass_data: dict[str, SmarwiDevice] = hass.data[DOMAIN][entry.entry_id]  # pyright:ignore[reportAny]

    async def async_discover_device(entry_id: str, device_id: str) -> None:
        if entry_id != entry.entry_id:  # pyright:ignore[reportAny]
            return  # not for us
        assert hass_data[device_id] is not None
        async_add_entities([SmarwiCover(hass_data[device_id])], True)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY_NEW, async_discover_device)
    )


class SmarwiCover(SmarwiEntity, CoverEntity):
    """Representation of a SMARWI Window Cover."""

    entity_description = CoverEntityDescription(
        key="cover",
        device_class=CoverDeviceClass.WINDOW,
    )  # pyright:ignore[reportCallIssue]

    _attr_supported_features = (
        CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.STOP_TILT
        | CoverEntityFeature.SET_TILT_POSITION
    )

    def __init__(self, device: SmarwiDevice):
        """Initialize the cover."""
        super().__init__(device)
        self._position = -1  # unknown
        self._requested_position = -1  # unknown
        self._is_moving = False

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def available(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._attr_available and not self.device.state_code.is_error()

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def is_closed(self) -> bool | None:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self.device.closed

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def is_closing(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._is_moving and self._requested_position < self._position

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def is_opening(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._is_moving and self._requested_position > self._position

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def current_cover_tilt_position(self) -> int | None:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._position if self._position >= 0 else None

    @override
    async def async_open_cover_tilt(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        self._requested_position = 100
        await self.device.async_open()

    @override
    async def async_close_cover_tilt(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        self._requested_position = 0
        await self.device.async_close()

    @override
    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        pos = int(kwargs[ATTR_TILT_POSITION])  # pyright:ignore[reportAny]
        self._requested_position = pos
        await self.device.async_open(pos)

    @override
    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        # If the motor is not moving, "stop" releases the ridge.
        if self.device.state_code.is_idle():
            return None

        self._requested_position = -1  # unknown
        self._position = -1  # unknown
        await self.device.async_stop()

    @override
    async def async_handle_update(self, changed_props: set[SmarwiDeviceProp]) -> None:
        if not changed_props & {SmarwiDeviceProp.CLOSED, SmarwiDeviceProp.STATE_CODE}:
            return

        state = self.device.state_code
        if state.is_error():
            self._is_moving = False
            self._position = -1
            self._requested_position = -1
        elif state.is_moving():
            self._is_moving = True
            if state.is_near_frame():
                self._position = NEAR_FRAME_POSITION
        elif state.is_idle():
            if self.device.closed:
                self._is_moving = False
                self._position = 0
                self._requested_position = 0
            elif self._is_moving:
                self._is_moving = False
                if self._requested_position >= 0:
                    self._position = self._requested_position
                    self._requested_position = -1
                else:
                    self._position = -1

        _LOGGER.debug(
            f"[{self.device.name}] id={self.device.id}, state_code={state.name}, closed={self.device.closed}, _is_moving={self._is_moving}, _position={self._position}, _requested_position={self._requested_position}"
        )
        self._attr_extra_state_attributes["state_code"] = state.name
        self._attr_extra_state_attributes["position"] = (
            self._position if self._position >= 0 else None
        )
        self.async_write_ha_state()


# Footnotes:
#
# [1] @cached_property is supposed to be reset on state update, but it doesn't
#     work here, even when I provide SmarwiCover(..., cached_properties={...}).
