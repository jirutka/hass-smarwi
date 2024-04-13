# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
from logging import Logger, getLogger
from typing import Final

LOGGER: Final[Logger] = getLogger(__package__)

NAME: Final = "SMARWI"
DOMAIN: Final = "smarwi"

DEVICE_INFO_MANUFACTURER: Final = "Vektiva"
DEVICE_INFO_MODEL: Final = "SMARWI"

CONF_REMOTE_ID: Final = "remote_id"

NEAR_FRAME_POSITION: Final = 5
"""The window position to be reported when it's between the frame and the frame sensor."""

SIGNAL_DISCOVERY_NEW: Final = f"{DOMAIN}.discovery_new"
"""Signal dispatched when a new SMARWI device is discovered."""


def signal_device_update(device_id: str) -> str:
    """Device specific event to signal a change in the status properties or availability."""
    return f"{DOMAIN}.{device_id}_update"
