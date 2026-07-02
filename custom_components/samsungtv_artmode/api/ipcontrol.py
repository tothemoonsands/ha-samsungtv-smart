"""Samsung IP Control JSON-RPC client.

This talks to the newer Samsung IP Control endpoint on HTTPS port 1516. On
2024 Frame TVs it gives an explicit Art Mode command path that is independent
of the legacy art-app websocket.
"""

from __future__ import annotations

import http.client
import json
import logging
import ssl
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DEFAULT_IP_CONTROL_PORT = 1516
JSONRPC_VERSION = "2.0"
CMD_TIMEOUT = 5
PAIR_TIMEOUT = 30

ERROR_UNAUTHORIZED = -32010
ERROR_PARSE_STALE_TOKEN = -32700


class SamsungIPControlError(Exception):
    """Base error for Samsung IP Control failures."""


class SamsungIPControlAuthError(SamsungIPControlError):
    """Access token is missing, invalid, or expired."""


class SamsungIPControl:
    """Minimal async client for Samsung IP Control."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        *,
        port: int = DEFAULT_IP_CONTROL_PORT,
        token: str | None = None,
    ) -> None:
        """Initialize the client."""
        self._hass = hass
        self._host = host
        self._port = port
        self._token = token
        self._ctx: ssl.SSLContext | None = None

    @property
    def token(self) -> str | None:
        """Return the current access token."""
        return self._token

    def set_token(self, token: str | None) -> None:
        """Update the current access token."""
        self._token = token

    async def async_pair(self) -> str:
        """Create an access token. The TV must be on and not in Art Mode."""
        result = await self._async_request(
            "createAccessToken", include_token=False, timeout=PAIR_TIMEOUT
        )
        token = result.get("AccessToken")
        if not isinstance(token, str) or not token:
            raise SamsungIPControlError(f"no AccessToken in response: {result!r}")
        self._token = token
        return token

    async def async_get_power_state(self) -> str:
        """Return powerOn, powerOff, or unknown."""
        result = await self._async_request("powerControl")
        return result.get("power", "unknown")

    async def async_power_on(self) -> str:
        """Power the TV on."""
        result = await self._async_request("powerControl", {"power": "powerOn"})
        return result.get("power", "unknown")

    async def async_get_art_mode(self) -> bool | None:
        """Return whether the panel is displaying Art Mode."""
        if await self.async_get_power_state() == "powerOff":
            return False

        result = await self._async_request("artModeControl")
        art_mode = result.get("artMode")
        if art_mode == "artModeOn":
            return True
        if art_mode == "artModeOff":
            return False
        return None

    async def async_set_art_mode(self, enabled: bool) -> None:
        """Explicitly enter or exit Art Mode."""
        value = "artModeOn" if enabled else "artModeOff"
        await self._async_request("artModeControl", {"artMode": value})

    async def async_get_device_information(self) -> dict[str, Any]:
        """Return basic TV device information."""
        return await self._async_request("getDeviceInformation")

    async def _async_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        include_token: bool = True,
        timeout: int = CMD_TIMEOUT,
    ) -> dict[str, Any]:
        """Run a blocking JSON-RPC request in the executor."""
        return await self._hass.async_add_executor_job(
            self._request, method, params or {}, include_token, timeout
        )

    def _request(
        self,
        method: str,
        params: dict[str, Any],
        include_token: bool,
        timeout: int,
    ) -> dict[str, Any]:
        """Send one JSON-RPC request."""
        payload_params = dict(params)
        if include_token:
            if not self._token:
                raise SamsungIPControlAuthError("missing IP Control token")
            payload_params["AccessToken"] = self._token

        payload = json.dumps(
            {
                "jsonrpc": JSONRPC_VERSION,
                "method": method,
                "params": payload_params,
                "id": 1,
            }
        )

        ctx = self._get_ssl_context()
        conn = http.client.HTTPSConnection(
            self._host,
            self._port,
            timeout=timeout,
            context=ctx,
        )
        try:
            conn.request(
                "POST",
                "/",
                body=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", errors="replace")
        except OSError as ex:
            raise SamsungIPControlError(str(ex)) from ex
        finally:
            conn.close()

        if resp.status >= 400:
            raise SamsungIPControlError(f"HTTP {resp.status}: {raw}")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as ex:
            raise SamsungIPControlError(f"invalid JSON response: {raw!r}") from ex

        if "error" in data:
            error = data["error"]
            code = error.get("code") if isinstance(error, dict) else None
            if code in (ERROR_UNAUTHORIZED, ERROR_PARSE_STALE_TOKEN):
                raise SamsungIPControlAuthError(str(error))
            raise SamsungIPControlError(str(error))

        result = data.get("result")
        if not isinstance(result, dict):
            raise SamsungIPControlError(f"invalid response: {data!r}")
        return result

    def _get_ssl_context(self) -> ssl.SSLContext:
        """Return an SSL context that accepts the TV's self-signed cert."""
        if self._ctx is None:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self._ctx = ctx
        return self._ctx
