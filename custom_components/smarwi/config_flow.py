# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2024 Jakub Jirutka <jakub@jirutka.cz>
"""Config flow for SMARWI integration."""

from typing import Any  # type:ignore[Any]
from typing_extensions import override

from homeassistant.config_entries import ConfigFlow, CONN_CLASS_LOCAL_PUSH, FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .const import CONF_REMOTE_ID, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        # TODO validate
        vol.Required(CONF_REMOTE_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT),
        ),
    }
)


class SmarwiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for SMARWI."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_PUSH

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(title="SMARWI", data=user_input)

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
