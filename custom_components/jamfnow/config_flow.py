from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import JamfNowAuthError, JamfNowClient
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    session = aiohttp_client.async_get_clientsession(hass)
    client = JamfNowClient(
        session=session,
        base_url=data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
    )
    await client.async_login()
    return {"title": data[CONF_USERNAME]}


class JamfNowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except JamfNowAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pragma: no cover - broad catch shown in UI
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
