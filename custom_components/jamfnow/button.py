
from __future__ import annotations

from typing import Callable, Awaitable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import JamfNowClient
from .const import DOMAIN
from .coordinator import JamfNowDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: JamfNowDataUpdateCoordinator = data["coordinator"]
    client: JamfNowClient = data["client"]

    entities: list[JamfNowActionButton] = []
    if coordinator.data:
        for device in coordinator.data.devices:
            entities.extend(
                [
                    JamfNowActionButton(
                        coordinator,
                        client,
                        device.id,
                        "restart",
                        "Restart Device",
                        client.async_restart_device,
                    ),
                    JamfNowActionButton(
                        coordinator,
                        client,
                        device.id,
                        "shutdown",
                        "Shut Down Device",
                        client.async_shutdown_device,
                    ),
                    JamfNowActionButton(
                        coordinator,
                        client,
                        device.id,
                        "lost_mode",
                        "Enable Lost Mode",
                        client.async_enable_lost_mode,
                    ),
                    JamfNowActionButton(
                        coordinator,
                        client,
                        device.id,
                        "disable_lost_mode",
                        "Disable Lost Mode",
                        client.async_disable_lost_mode,
                    ),
                ]
            )
    async_add_entities(entities)


class JamfNowActionButton(ButtonEntity):

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JamfNowDataUpdateCoordinator,
        client: JamfNowClient,
        device_id: str,
        action_key: str,
        name: str,
        action: Callable[..., Awaitable[None]],
    ) -> None:
        self.coordinator = coordinator
        self.client = client
        self._device_id = device_id
        self._action_key = action_key
        self._attr_unique_id = f"{device_id}_{action_key}_button"
        self._attr_name = name
        self._action = action

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.get_device(self._device_id)
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.name if device else "Jamf Now Device",
            manufacturer="Apple",
            model=device.model if device else None,
            serial_number=device.serial_number if device else None,
        )

    async def async_press(self) -> None:
        if self._action_key in {"lost_mode", "disable_lost_mode"}:
            device = self.coordinator.get_device(self._device_id)
            if device and device.supervised is False:
                raise ValueError("Lost Mode actions are only available for supervised devices")
        await self._action(self._device_id)
        await self.coordinator.async_request_refresh()
