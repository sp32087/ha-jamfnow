
from __future__ import annotations

from typing import List

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import JamfNowClient, JamfNowDevice
from .const import DOMAIN
from .coordinator import JamfNowDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: JamfNowDataUpdateCoordinator = data["coordinator"]
    client: JamfNowClient = data["client"]

    entities: list[JamfNowBlueprintSelect] = []
    if coordinator.data:
        for device in coordinator.data.devices:
            entities.append(JamfNowBlueprintSelect(coordinator, client, device.id))
    async_add_entities(entities)


class JamfNowBlueprintSelect(SelectEntity):

    _attr_has_entity_name = True
    _attr_translation_key = "blueprint_select"

    def __init__(
        self,
        coordinator: JamfNowDataUpdateCoordinator,
        client: JamfNowClient,
        device_id: str,
    ) -> None:
        self.coordinator = coordinator
        self.client = client
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_blueprint_select"

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

    @property
    def name(self) -> str | None:
        device = self.coordinator.get_device(self._device_id)
        return f"{device.name if device else 'Device'} Blueprint"

    @property
    def options(self) -> list[str]:
        if not self.coordinator.data:
            return []
        return [self._format_option(bp.name, bp.id) for bp in self.coordinator.data.blueprints]

    @property
    def current_option(self) -> str | None:
        device = self.coordinator.get_device(self._device_id)
        if not device or not device.blueprint_id or not self.coordinator.data:
            return None
        for bp in self.coordinator.data.blueprints:
            if str(bp.id) == str(device.blueprint_id):
                return self._format_option(bp.name, bp.id)
        return None

    async def async_select_option(self, option: str) -> None:
        blueprint_id = self._parse_option(option)
        await self.client.async_set_blueprint(self._device_id, blueprint_id)
        await self.coordinator.async_request_refresh()

    @staticmethod
    def _format_option(name: str, blueprint_id: str) -> str:
        return f"{name} ({blueprint_id})"

    @staticmethod
    def _parse_option(option: str) -> str:
        if option.endswith(")") and "(" in option:
            return option.rsplit("(", 1)[-1].rstrip(")")
        return option
