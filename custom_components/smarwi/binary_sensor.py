# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
from typing_extensions import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # pyright:ignore[reportUnknownVariableType]
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW
from .device import SmarwiDeviceProp, SmarwiDevice
from .entity import SmarwiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMARWI binary sensor entities based on a config entry."""
    hass_data: dict[str, SmarwiDevice] = hass.data[DOMAIN][entry.entry_id]  # pyright:ignore[reportAny]

    async def async_discover_device(entry_id: str, device_id: str) -> None:
        if entry_id != entry.entry_id:
            return  # not for us
        assert hass_data[device_id] is not None
        async_add_entities([SmarwiRidgeInsideBinarySensor(hass_data[device_id])])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY_NEW, async_discover_device)
    )


class SmarwiRidgeInsideBinarySensor(SmarwiEntity, BinarySensorEntity):
    """Representation of the SMARWI "ridge inside" sensor."""

    entity_description = BinarySensorEntityDescription(
        key="ridge_inside",
        device_class=BinarySensorDeviceClass.TAMPER,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    @override
    async def async_handle_update(self, changed_props: set[SmarwiDeviceProp]) -> None:
        if SmarwiDeviceProp.RIDGE_INSIDE in changed_props:
            self._attr_is_on = not self.device.ridge_inside
            self.async_write_ha_state()
