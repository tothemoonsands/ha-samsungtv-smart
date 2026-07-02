"""Tests for the Samsung Frame TV Art API websocket connection handling."""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.samsungtv_artmode.api.art import (
    MS_CHANNEL_CONNECT_EVENT,
    MS_CHANNEL_READY_EVENT,
    SamsungTVAsyncArt,
)


@pytest.mark.asyncio
async def test_open_falls_back_from_secure_port(caplog: pytest.LogCaptureFixture) -> None:
    """The art client should fall back from port 8002 to 8001."""
    ready_message = MagicMock(
        type=aiohttp.WSMsgType.TEXT,
        data=json.dumps({"event": MS_CHANNEL_READY_EVENT}),
    )
    ws = MagicMock(closed=False)
    ws.receive = AsyncMock(return_value=ready_message)

    session = MagicMock(closed=False)
    session.ws_connect = AsyncMock(side_effect=[ConnectionRefusedError("refused"), ws])

    art = SamsungTVAsyncArt("192.168.1.38", port=8002, token="token", session=session)

    with caplog.at_level(logging.DEBUG):
        assert await art.open() is True

    assert art._port == 8001
    assert session.ws_connect.await_count == 2
    assert session.ws_connect.await_args_list[0].args[0].startswith(
        "wss://192.168.1.38:8002/"
    )
    assert session.ws_connect.await_args_list[1].args[0].startswith(
        "ws://192.168.1.38:8001/"
    )
    assert "trying fallback" in caplog.text


@pytest.mark.asyncio
async def test_open_does_not_send_remote_token_to_art_channel() -> None:
    """The art-app channel should be opened without the remote-control token."""
    ready_message = MagicMock(
        type=aiohttp.WSMsgType.TEXT,
        data=json.dumps({"event": MS_CHANNEL_READY_EVENT}),
    )
    ws = MagicMock(closed=False)
    ws.receive = AsyncMock(return_value=ready_message)

    session = MagicMock(closed=False)
    session.ws_connect = AsyncMock(return_value=ws)

    art = SamsungTVAsyncArt("192.168.1.38", port=8002, token="secret", session=session)

    assert await art.open() is True
    assert "token=secret" not in session.ws_connect.await_args.args[0]


@pytest.mark.asyncio
async def test_open_accepts_connect_without_ready() -> None:
    """Some Frame TVs send connect but never emit ms.channel.ready."""
    connect_message = MagicMock(
        type=aiohttp.WSMsgType.TEXT,
        data=json.dumps({"event": MS_CHANNEL_CONNECT_EVENT}),
    )
    ws = MagicMock(closed=False)
    ws.receive = AsyncMock(return_value=connect_message)

    session = MagicMock(closed=False)
    session.ws_connect = AsyncMock(return_value=ws)

    art = SamsungTVAsyncArt("192.168.1.38", port=8001, session=session)

    assert await art.open() is True


@pytest.mark.asyncio
async def test_open_logs_one_warning_after_all_ports_fail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The art client should emit one summary warning after all attempts fail."""
    session = MagicMock(closed=False)
    session.ws_connect = AsyncMock(
        side_effect=[
            ConnectionRefusedError("refused-8002"),
            ConnectionRefusedError("refused-8001"),
        ]
    )

    art = SamsungTVAsyncArt("192.168.1.38", port=8002, token="token", session=session)

    with caplog.at_level(logging.WARNING):
        assert await art.open() is False

    warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "trying ports [8002, 8001]" in warnings[0]
