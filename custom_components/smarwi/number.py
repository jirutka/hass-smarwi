# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
from typing_extensions import override

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect  # pyright:ignore[reportUnknownVariableType]
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY_NEW
from .device import SmarwiDeviceProp, FinetuneSetting, SmarwiDevice
from .entity import SmarwiEntity


SETTINGS_ENTITY_DESCRIPTIONS = [
    NumberEntityDescription(
        key=FinetuneSetting.CALIBRATED_DISTANCE.name,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        entity_registry_enabled_default=False,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key=FinetuneSetting.CLOSED_POSITION.name,
        entity_category=EntityCategory.CONFIG,
        native_min_value=-20,
        native_max_value=20,
        native_step=1,
    ),
    NumberEntityDescription(
        key=FinetuneSetting.LOCK_ERR_TRIGGER.name,
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=40,
        native_step=1,
    ),
    *(
        NumberEntityDescription(
            key=key.name,
            entity_category=EntityCategory.CONFIG,
            native_min_value=0,
            native_max_value=100,
            native_unit_of_measurement="%",
        )
        for key in FinetuneSetting
        if key
        not in (
            FinetuneSetting.CALIBRATED_DISTANCE,
            FinetuneSetting.CLOSED_POSITION,
            FinetuneSetting.LOCK_ERR_TRIGGER,
        )
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMARWI number entities based on a config entry."""
    hass_data: dict[str, SmarwiDevice] = hass.data[DOMAIN][entry.entry_id]  # pyright:ignore[reportAny]

    async def async_discover_device(entry_id: str, device_id: str) -> None:
        if entry_id != entry.entry_id:
            return  # not for us
        assert hass_data[device_id] is not None

        entities = [
            SmarwiConfigNumber(hass_data[device_id], desc)
            for desc in SETTINGS_ENTITY_DESCRIPTIONS
        ]
        async_add_entities(entities)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_DISCOVERY_NEW, async_discover_device)
    )


class SmarwiConfigNumber(SmarwiEntity, NumberEntity):
    """Representation of SMARWI setting."""

    def __init__(
        self, device: SmarwiDevice, description: NumberEntityDescription
    ) -> None:
        """Initialize Entity."""
        self.entity_description = description
        self._attr_translation_key = description.key.lower()
        super().__init__(device)
        self._setting_key = FinetuneSetting[description.key]

    @property  # superclass uses @cached_property, but that doesn't work here
    @override
    def available(self) -> bool:  # pyright:ignore[reportIncompatibleVariableOverride]
        return self._attr_available and self._attr_native_value is not None

    @override
    async def async_set_native_value(self, value: float) -> None:
        await self.device.finetune_settings.async_set(self._setting_key, int(value))

    @override
    async def async_handle_update(self, changed_props: set[SmarwiDeviceProp]) -> None:
        if SmarwiDeviceProp.FINETUNE_SETTINGS in changed_props:
            if (
                value := self.device.finetune_settings.get(self._setting_key)
            ) is not None:
                self._attr_native_value = value
                self.async_write_ha_state()
