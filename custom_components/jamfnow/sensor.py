
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import JamfNowDevice
from .const import DOMAIN
from .coordinator import JamfNowDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class JamfNowSensorDescription(SensorEntityDescription):

    value_fn: Callable[[JamfNowDevice], str | None]


SENSOR_DESCRIPTIONS: tuple[JamfNowSensorDescription, ...] = (
    JamfNowSensorDescription(
        key="supervised",
        name="Supervised",
        value_fn=lambda device: "SUPERVISED" if device.supervised else ("UNSUPERVISED" if device.supervised is False else None),
    ),
    JamfNowSensorDescription(
        key="status",
        name="Jamf Now Status",
        value_fn=lambda device: device.status,
    ),
    JamfNowSensorDescription(
        key="os_version",
        name="OS Version",
        value_fn=lambda device: device.os_version,
    ),
    JamfNowSensorDescription(
        key="blueprint",
        name="Blueprint",
        value_fn=lambda device: device.blueprint_id,
    ),
    JamfNowSensorDescription(
        key="last_check_in",
        name="Last Check-in",
        value_fn=lambda device: device.last_check_in,
    ),
    JamfNowSensorDescription(
        key="lost_mode",
        name="Lost Mode Status",
        value_fn=lambda device: device.lost_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: JamfNowDataUpdateCoordinator = data["coordinator"]

    entities: list[JamfNowSensor] = []
    if coordinator.data:
        for device in coordinator.data.devices:
            for description in SENSOR_DESCRIPTIONS:
                entities.append(JamfNowSensor(coordinator, device.id, description))

    async_add_entities(entities)


class JamfNowSensor(CoordinatorEntity[JamfNowDataUpdateCoordinator], SensorEntity):

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: JamfNowDataUpdateCoordinator,
        device_id: str,
        description: JamfNowSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.get_device(self._device_id)
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.name if device else "Jamf Now Device",
            manufacturer="Apple",
            model=device.model if device else None,
            serial_number=device.serial_number if device else None,
            sw_version=device.os_version if device else None,
        )

    @property
    def native_value(self) -> str | None:
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None
        value = self.entity_description.value_fn(device)
        if self.entity_description.key == "blueprint" and value and self.coordinator.data:
            for bp in self.coordinator.data.blueprints:
                if str(bp.id) == str(value):
                    return bp.name
        return value
