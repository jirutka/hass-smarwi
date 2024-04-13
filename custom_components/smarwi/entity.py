# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
"""Support for SMARWI entities."""

from abc import abstractmethod
from typing_extensions import override

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import (
    DEVICE_INFO_MANUFACTURER,
    DEVICE_INFO_MODEL,
    DOMAIN,
)
from .device import SmarwiDeviceProp, SmarwiDevice


class SmarwiEntity(Entity):
    """Base class for SMARWI entities."""

    # NOTE: Do not set _attr_entity_name, it breaks localization!
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: SmarwiDevice) -> None:
        """Initialize Entity."""
        super().__init__()

        if self.entity_description and not self.translation_key:
            self._attr_translation_key = self.entity_description.key

        assert self.translation_key is not None, "translation_key is not set"

        self.device = device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device.id)},
            manufacturer=DEVICE_INFO_MANUFACTURER,
            model=DEVICE_INFO_MODEL,
        )
        self._attr_unique_id = f"{device.id}_{self.translation_key}"
        self._attr_extra_state_attributes = {}

    @override
    async def async_added_to_hass(self) -> None:
        async def update_handler(changed_keys: set[SmarwiDeviceProp]) -> None:
            if SmarwiDeviceProp.AVAILABLE in changed_keys:
                self._attr_available = self.device.available

            await self.async_handle_update(changed_keys)

            if SmarwiDeviceProp.AVAILABLE in changed_keys:
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.device.signal_update,
                update_handler,
            )
        )

    @abstractmethod
    async def async_handle_update(self, changed_props: set[SmarwiDeviceProp]) -> None:
        """When the device data has been updated."""
        pass
