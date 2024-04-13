# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
"""Constants for the SMARWI integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "SMARWI"
DOMAIN = "smarwi"

DEVICE_INFO_MANUFACTURER = "Vektiva"
DEVICE_INFO_MODEL = "SMARWI"

CONF_REMOTE_ID = "remote_id"

# The window position to be reported when it's between the frame and the frame sensor.
NEAR_FRAME_POSITION = 5

SIGNAL_DISCOVERY_NEW = f"{DOMAIN}_discovery_new"
