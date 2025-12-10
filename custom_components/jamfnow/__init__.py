
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import aiohttp_client, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .api import JamfNowAuthError, JamfNowClient
from .const import (
    CONF_BASE_URL,
    DEFAULT_BASE_URL,
    DOMAIN,
    PLATFORMS,
    SERVICE_ENABLE_LOST_MODE,
    SERVICE_DISABLE_LOST_MODE,
    SERVICE_RESTART_DEVICE,
    SERVICE_SET_BLUEPRINT,
    SERVICE_SHUTDOWN_DEVICE,
    SERVICE_SYNC_INVENTORY,
)
from .coordinator import JamfNowDataUpdateCoordinator

JamfNowConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {"services_registered": False})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: JamfNowConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    client = JamfNowClient(
        session=session,
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    await client.async_login()

    coordinator = JamfNowDataUpdateCoordinator(hass, client=client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.data[DOMAIN].get("services_registered"):
        _register_services(hass)
        hass.data[DOMAIN]["services_registered"] = True

    return True


async def async_unload_entry(hass: HomeAssistant, entry: JamfNowConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    async def _resolve_client_and_coordinator(
        device_id: str,
    ) -> tuple[JamfNowClient, JamfNowDataUpdateCoordinator] | None:
        for entry_id, data in hass.data.get(DOMAIN, {}).items():
            if entry_id == "services_registered":
                continue
            coordinator: JamfNowDataUpdateCoordinator = data["coordinator"]
            if coordinator.device_present(device_id):
                return data["client"], coordinator
        return None

    def _extract_jamf_device_id(call: ServiceCall) -> str:
        if call.data.get("entity_id"):
            raise ValueError("Please select a Jamf Now device, not an entity")
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        device_id = device_ids[0]
        registry = dr.async_get(hass)
        device = registry.async_get(device_id)
        if not device:
            raise ValueError(f"Home Assistant device {device_id} not found")
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                return identifier[1]
        raise ValueError("Device is not a Jamf Now device")

    async def handle_set_blueprint(call: ServiceCall) -> None:
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        jamf_device_id = _extract_jamf_device_id(call)
        blueprint_id: str = call.data["blueprint_id"]
        resolved = await _resolve_client_and_coordinator(jamf_device_id)
        if not resolved:
            raise ValueError(f"Device {jamf_device_id} not found in Jamf Now data")
        client, coordinator = resolved
        await client.async_set_blueprint(jamf_device_id, blueprint_id)
        await coordinator.async_request_refresh()

    async def handle_enable_lost_mode(call: ServiceCall) -> None:
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        message: str | None = call.data.get("message")
        phone: str | None = call.data.get("phone") or ""
        footnote: str | None = call.data.get("footnote")
        play_sound: bool | None = call.data.get("play_sound")
        jamf_device_id = _extract_jamf_device_id(call)
        resolved = await _resolve_client_and_coordinator(jamf_device_id)
        if not resolved:
            raise ValueError(f"Device {jamf_device_id} not found in Jamf Now data")
        client, coordinator = resolved
        message_to_send = message or "Lost mode enabled via Home Assistant"
        device = coordinator.get_device(jamf_device_id)
        if device and device.supervised is False:
            raise ValueError("Lost Mode can only be enabled on supervised devices")
        await client.async_enable_lost_mode(
            jamf_device_id,
            message=message_to_send,
            phone=phone,
            footnote=footnote,
            play_sound=play_sound,
        )
        await coordinator.async_request_refresh()

    async def handle_restart(call: ServiceCall) -> None:
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        jamf_device_id = _extract_jamf_device_id(call)
        resolved = await _resolve_client_and_coordinator(jamf_device_id)
        if not resolved:
            raise ValueError(f"Device {jamf_device_id} not found in Jamf Now data")
        client, coordinator = resolved
        await client.async_restart_device(jamf_device_id)
        await coordinator.async_request_refresh()

    async def handle_disable_lost_mode(call: ServiceCall) -> None:
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        jamf_device_id = _extract_jamf_device_id(call)
        resolved = await _resolve_client_and_coordinator(jamf_device_id)
        if not resolved:
            raise ValueError(f"Device {jamf_device_id} not found in Jamf Now data")
        client, coordinator = resolved
        device = coordinator.get_device(jamf_device_id)
        if device and device.supervised is False:
            raise ValueError("Lost Mode can only be disabled on supervised devices")
        await client.async_disable_lost_mode(jamf_device_id)
        await coordinator.async_request_refresh()

    async def handle_shutdown(call: ServiceCall) -> None:
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        jamf_device_id = _extract_jamf_device_id(call)
        resolved = await _resolve_client_and_coordinator(jamf_device_id)
        if not resolved:
            raise ValueError(f"Device {jamf_device_id} not found in Jamf Now data")
        client, coordinator = resolved
        await client.async_shutdown_device(jamf_device_id)
        await coordinator.async_request_refresh()

    async def handle_sync_inventory(call: ServiceCall) -> None:
        device_ids: list[str] = call.data.get("device_id") or []
        if len(device_ids) != 1:
            raise ValueError("Select exactly one Jamf Now device")
        jamf_device_id = _extract_jamf_device_id(call)
        resolved = await _resolve_client_and_coordinator(jamf_device_id)
        if not resolved:
            raise ValueError(f"Device {jamf_device_id} not found in Jamf Now data")
        client, coordinator = resolved
        await client.async_sync_inventory(jamf_device_id)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BLUEPRINT,
        handle_set_blueprint,
        vol.Schema(
            {
                vol.Required("device_id"): [str],
                vol.Required("blueprint_id"): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE_LOST_MODE,
        handle_enable_lost_mode,
        vol.Schema(
            {
                vol.Required("device_id"): [str],
                vol.Optional("message"): str,
                vol.Optional("phone"): str,
                vol.Optional("footnote"): str,
                vol.Optional("play_sound"): bool,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_DEVICE,
        handle_restart,
        vol.Schema({vol.Required("device_id"): [str]}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE_LOST_MODE,
        handle_disable_lost_mode,
        vol.Schema({vol.Required("device_id"): [str]}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SHUTDOWN_DEVICE,
        handle_shutdown,
        vol.Schema({vol.Required("device_id"): [str]}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_INVENTORY,
        handle_sync_inventory,
        vol.Schema({vol.Required("device_id"): [str]}),
    )
