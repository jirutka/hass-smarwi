# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
from typing import Any, cast  # pyright:ignore[reportAny]
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
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # pyright:ignore[reportUnknownVariableType]
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER, NEAR_FRAME_POSITION, SIGNAL_DISCOVERY_NEW
from .device import SmarwiDeviceProp, SmarwiDevice
from .entity import SmarwiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SMARWI window cover entities."""
    hass_data: dict[str, SmarwiDevice] = hass.data[DOMAIN][entry.entry_id]  # pyright:ignore[reportAny]

    async def async_discover_device(entry_id: str, device_id: str) -> None:
        if entry_id != cast(str, entry.entry_id):  # pyright:ignore[reportAny]
            return  # not for us
        assert hass_data[device_id] is not None
        async_add_entities([SmarwiCover(hass_data[device_id])])

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
        self._requested_position = -1  # unknown/none
        self._is_moving = False

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def available(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        return (
            self._attr_available
            and self.device.ridge_fixed
            and not self.device.state_code.is_error()
        )

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def is_closed(self) -> bool | None:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self.device.closed

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def is_closing(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._is_moving and not self.is_opening

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def is_opening(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        # NOTE: SMARWI reports OPENING even when closing to a position,
        #  so we don't rely on the state_code if we have _requested_position.
        if self._requested_position >= 0:
            return self._is_moving and self._requested_position > self._position
        else:  # if initiated outside of HASS
            return self.device.state_code.is_opening()

    @property  # superclass uses @cached_property, but that doesn't work here [1]
    @override
    def current_cover_tilt_position(self) -> int | None:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._position if self._position >= 0 else None

    @override
    async def async_open_cover_tilt(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        if self._position != 100:
            self._requested_position = 100
            await self.device.async_open()

    @override
    async def async_close_cover_tilt(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        if self._position != 0:
            self._requested_position = 0
            await self.device.async_close()

    @override
    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        pos = int(kwargs[ATTR_TILT_POSITION])  # pyright:ignore[reportAny]
        if self._position != pos:
            self._requested_position = pos
            await self.device.async_open(pos)

    @override
    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:  # pyright:ignore[reportAny]
        # Do nothing if the motor is not moving.
        if self.device.state_code.is_idle():
            return None

        self._requested_position = -1  # unknown/none
        self._position = -1  # unknown
        await self.device.async_stop()

    @override
    async def async_handle_update(self, changed_props: set[SmarwiDeviceProp]) -> None:
        if not changed_props & {
            SmarwiDeviceProp.CLOSED,
            SmarwiDeviceProp.RIDGE_FIXED,
            SmarwiDeviceProp.STATE_CODE,
        }:
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
                self._requested_position = -1
            elif self._is_moving:
                self._is_moving = False
                if self._requested_position >= 0:
                    self._position = self._requested_position
                else:
                    self._position = -1
                self._requested_position = -1

        LOGGER.debug(
            f"[{self.device.name}] id={self.device.id}, state_code={state.name}, closed={self.device.closed}, _is_moving={self._is_moving}, _position={self._position}, _requested_position={self._requested_position}"
        )
        self._attr_extra_state_attributes["state_code"] = state.name
        self.async_write_ha_state()


# Footnotes:
#
# [1] @cached_property is supposed to be reset on state update, but it doesn't
#     work here, even when I provide SmarwiCover(..., cached_properties={...}).
