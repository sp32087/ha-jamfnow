
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp


class JamfNowError(Exception):
    pass


class JamfNowAuthError(JamfNowError):
    pass


class JamfNowApiError(JamfNowError):
    pass


@dataclass
class JamfNowBlueprint:

    id: str
    name: str
    description: str | None = None


@dataclass
class JamfNowDevice:

    id: str
    name: str
    serial_number: str
    model: str | None
    os_version: str | None
    status: str | None
    blueprint_id: str | None
    last_check_in: str | None
    lost_mode: str | None
    supervised: bool | None = None


class JamfNowClient:

    def __init__(self, session: aiohttp.ClientSession, base_url: str, username: str, password: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._logged_in = False

    async def _ensure_login(self) -> None:
        if self._logged_in:
            return
        await self.async_login()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{path}"
        for attempt in range(2):
            if not self._logged_in:
                await self._ensure_login()
            try:
                async with self._session.request(method, url, **kwargs) as resp:
                    if resp.status == 401:
                        if attempt == 0:
                            self._logged_in = False
                            continue
                        raise JamfNowAuthError("Invalid credentials for Jamf Now")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise JamfNowApiError(f"Jamf Now API error {resp.status}: {text}")
                    if "application/json" in resp.headers.get("Content-Type", ""):
                        return await resp.json()
                    return await resp.text()
            except aiohttp.ClientError as err:
                raise JamfNowApiError(f"Connection error: {err}") from err
        raise JamfNowAuthError("Authentication failed after retry")

    async def async_login(self) -> None:
        login_url = f"{self._base_url}/login/auth"
        payload = {
            "username": self._username,
            "password": self._password,
            "lang": "en-US",
        }

        try:
            async with self._session.post(login_url, data=payload) as resp:
                if resp.status == 401:
                    raise JamfNowAuthError("Invalid credentials for Jamf Now")
                if resp.status >= 400:
                    text = await resp.text()
                    raise JamfNowApiError(f"Login failed {resp.status}: {text}")

                if not resp.headers.get("x-ajax-location"):
                    raise JamfNowAuthError("Login failed: no redirect provided")

                self._logged_in = True
        except aiohttp.ClientError as err:
            raise JamfNowApiError(f"Connection error during login: {err}") from err

    async def async_get_blueprints(self) -> list[JamfNowBlueprint]:
        data = await self._request("GET", "/frontend/rest/blueprints")
        blueprints: list[JamfNowBlueprint] = []
        for item in data if isinstance(data, list) else data.get("blueprints", []):
            blueprints.append(
                JamfNowBlueprint(
                    id=str(item.get("blueprintId") or item.get("id")),
                    name=item.get("name") or "Unknown",
                    description=item.get("description") or item.get("openEnrollmentSlug"),
                )
            )
        return blueprints

    async def async_get_devices(self) -> list[JamfNowDevice]:
        data = await self._request("GET", "/device-status/devices")
        devices: list[JamfNowDevice] = []
        for item in data if isinstance(data, list) else data.get("devices", []):
            blueprint = item.get("blueprint") or {}
            lost_mode_raw = (
                item.get("lostModeStatus")
                or item.get("lost_mode_status")
                or item.get("lostMode")
                or item.get("lost_mode")
                or item.get("lostModeEnabled")
                or item.get("lostModeOn")
            )
            if isinstance(lost_mode_raw, bool):
                lost_mode = "ENABLED" if lost_mode_raw else "DISABLED"
            elif isinstance(lost_mode_raw, str):
                lost_mode = lost_mode_raw
            else:
                lost_mode = None
            devices.append(
                JamfNowDevice(
                    id=str(item.get("deviceId") or item.get("id")),
                    name=item.get("inventoryName") or item.get("deviceName") or item.get("name") or "Unknown",
                    serial_number=item.get("serialNumber") or item.get("serial_number") or "unknown",
                    model=item.get("modelIdentifier") or item.get("model"),
                    os_version=item.get("osVersion") or item.get("os_version"),
                    status=item.get("status") or item.get("managementStatus"),
                    blueprint_id=(str(item.get("blueprintId")) if item.get("blueprintId") is not None else None)
                    or (str(item.get("blueprint_id")) if item.get("blueprint_id") is not None else None)
                    or (str(blueprint.get("blueprintId")) if blueprint else None),
                    last_check_in=item.get("lastInventoryTime")
                    or item.get("lastCheckIn")
                    or item.get("last_check_in"),
                    lost_mode=lost_mode,
                    supervised=item.get("supervised"),
                )
            )
        results = await asyncio.gather(
            *(self.async_get_device(device.id) for device in devices),
            return_exceptions=True,
        )
        for device, detail in zip(devices, results):
            if isinstance(detail, Exception):
                continue
            lost_info = (detail.get("status") or {}).get("lostModeInfo") or {}
            status = lost_info.get("status")
            if status:
                device.lost_mode = status
            device.supervised = detail.get("supervised", device.supervised)
        return devices

    async def async_get_device(self, device_id: str) -> Dict[str, Any]:
        data = await self._request("GET", f"/frontend/rest/devices/{device_id}")
        if isinstance(data, dict):
            return data
        raise JamfNowApiError("Unexpected device response structure")

    async def async_set_blueprint(self, device_id: str, blueprint_id: str) -> None:
        payload = {"deviceIds": [device_id], "depSerialNumbers": []}
        await self._request("POST", f"/frontend/rest/blueprints/{blueprint_id}/devices", json=payload)

    async def async_enable_lost_mode(
        self,
        device_id: str,
        message: str | None = None,
        phone: str | None = None,
        footnote: str | None = None,
        play_sound: bool | None = None,
    ) -> None:
        payload: Dict[str, Any] = {}
        payload["message"] = message or "Lost mode enabled via Home Assistant"
        payload["phoneNumber"] = phone or ""
        if footnote:
            payload["footNote"] = footnote
        if play_sound is not None:
            payload["playSoundImmediately"] = play_sound
        await self._request("POST", f"/frontend/rest/devices/{device_id}/lost", json=payload)

    async def async_disable_lost_mode(self, device_id: str) -> None:
        await self._request("DELETE", f"/frontend/rest/devices/{device_id}/lost")

    async def async_restart_device(self, device_id: str) -> None:
        await self._request("POST", f"/frontend/rest/devices/{device_id}/restart")

    async def async_shutdown_device(self, device_id: str) -> None:
        await self._request("POST", f"/frontend/rest/devices/{device_id}/shutdown")

    async def async_sync_inventory(self, device_id: str) -> None:
        await self._request("POST", f"/frontend/rest/devices/{device_id}/sync/inventory")

    async def async_assign_blueprint(self, device_id: str, blueprint_id: str) -> None:
        payload = {"deviceIds": [device_id], "depSerialNumbers": []}
        await self._request("POST", f"/frontend/rest/blueprints/{blueprint_id}/devices", json=payload)
