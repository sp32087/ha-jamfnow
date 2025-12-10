
from __future__ import annotations

from datetime import timedelta
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JamfNowBlueprint, JamfNowClient, JamfNowDevice
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class JamfNowData:

    def __init__(self, devices: list[JamfNowDevice], blueprints: list[JamfNowBlueprint]) -> None:
        self.devices = devices
        self.blueprints = blueprints


class JamfNowDataUpdateCoordinator(DataUpdateCoordinator[JamfNowData]):

    def __init__(self, hass: HomeAssistant, client: JamfNowClient) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> JamfNowData:
        try:
            devices = await self.client.async_get_devices()
            blueprints = await self.client.async_get_blueprints()
            return JamfNowData(devices=devices, blueprints=blueprints)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Jamf Now: {err}") from err

    def device_present(self, device_id: str) -> bool:
        if not self.data:
            return False
        return any(device.id == device_id for device in self.data.devices)

    def get_device(self, device_id: str) -> JamfNowDevice | None:
        if not self.data:
            return None
        for device in self.data.devices:
            if device.id == device_id:
                return device
        return None
