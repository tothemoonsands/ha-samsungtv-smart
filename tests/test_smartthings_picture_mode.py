"""Tests for SmartThings picture mode id selection."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.samsungtv_artmode.api.smartthings import STStatus, SmartThingsTV


PICTURE_MODE_MAP = [
    {"name": "Dynamic", "id": "modeDynamicHDR"},
    {"name": "Movie", "id": "modeMovieHDR"},
    {"name": "FILMMAKER MODE", "id": "modeFilmmakerModeHDR"},
    {"name": "Dynamic", "id": "modeDynamic"},
    {"name": "Movie", "id": "modeMovie"},
    {"name": "FILMMAKER MODE", "id": "modeFilmmakerMode"},
]


def test_picture_mode_mapping_defaults_to_sdr_when_signal_family_unknown() -> None:
    """Friendly picture modes should prefer SDR ids when current mode is unknown."""
    assert (
        SmartThingsTV._get_map_id_from_name("Movie", PICTURE_MODE_MAP)
        == "modeMovie"
    )


def test_picture_mode_mapping_preserves_current_hdr_signal_family() -> None:
    """Friendly picture modes should choose HDR ids while current mode is HDR."""
    assert (
        SmartThingsTV._get_map_id_from_name(
            "Movie", PICTURE_MODE_MAP, "modeFilmmakerModeHDR"
        )
        == "modeMovieHDR"
    )


def test_picture_mode_mapping_preserves_current_sdr_signal_family() -> None:
    """Friendly picture modes should choose SDR ids while current mode is SDR."""
    assert (
        SmartThingsTV._get_map_id_from_name(
            "FILMMAKER MODE", PICTURE_MODE_MAP, "modeMovie"
        )
        == "modeFilmmakerMode"
    )


def test_picture_mode_mapping_accepts_exact_mode_ids() -> None:
    """Exact SmartThings mode ids should pass through unchanged."""
    assert (
        SmartThingsTV._get_map_id_from_name("modeMovieHDR", PICTURE_MODE_MAP)
        == "modeMovieHDR"
    )


def test_picture_mode_mapping_uses_known_samsung_ids_without_runtime_map() -> None:
    """Common Samsung picture modes should map to ids when no map is reported."""
    assert SmartThingsTV._get_map_id_from_name("Movie", None) == "modeMovie"


def _picture_mode_tv() -> SmartThingsTV:
    tv = SmartThingsTV("token", "device-id", session=MagicMock())
    tv._state = STStatus.STATE_ON
    tv._picture_mode_list = ["Dynamic", "Movie", "FILMMAKER MODE"]
    tv._picture_mode_map = PICTURE_MODE_MAP
    tv._async_send_command = AsyncMock()
    return tv


@pytest.mark.asyncio
async def test_set_picture_mode_skips_matching_friendly_mode() -> None:
    """Repeated friendly mode automation calls should not resend commands."""
    tv = _picture_mode_tv()
    tv._picture_mode = "Movie"
    tv._picture_mode_id = "modeMovie"

    assert await tv.async_set_picture_mode("Movie") is False

    tv._async_send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_picture_mode_skips_matching_exact_mode_id() -> None:
    """Repeated exact id automation calls should not resend commands."""
    tv = _picture_mode_tv()
    tv._picture_mode = "Movie"
    tv._picture_mode_id = "modeMovieHDR"

    assert await tv.async_set_picture_mode("modeMovieHDR") is False

    tv._async_send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_picture_mode_sends_exact_id_when_signal_family_differs() -> None:
    """Exact SDR/HDR ids remain distinct even when the friendly name matches."""
    tv = _picture_mode_tv()
    tv._picture_mode = "Movie"
    tv._picture_mode_id = "modeMovieHDR"

    assert await tv.async_set_picture_mode("modeMovie") is True

    tv._async_send_command.assert_awaited_once()
    assert tv._picture_mode_id == "modeMovie"
    assert tv._picture_mode == "Movie"


@pytest.mark.asyncio
async def test_set_picture_mode_sends_friendly_name() -> None:
    """Samsung accepts friendly picture mode names even when ids are mapped."""
    tv = _picture_mode_tv()
    tv._picture_mode = "Movie"
    tv._picture_mode_id = "Movie"

    assert await tv.async_set_picture_mode("FILMMAKER MODE") is True

    tv._async_send_command.assert_awaited_once()
    data_cmd = tv._async_send_command.await_args.args[0]
    assert "FILMMAKER MODE" in data_cmd
    assert "modeFilmmakerModeHDR" not in data_cmd
    assert tv._picture_mode_id == "FILMMAKER MODE"
    assert tv._picture_mode == "FILMMAKER MODE"


@pytest.mark.asyncio
async def test_set_picture_mode_uses_friendly_name_after_default_map_fallback() -> None:
    """Optimistic state should stay friendly when only built-in ids are available."""
    tv = _picture_mode_tv()
    tv._picture_mode_list = []
    tv._picture_mode_map = None

    assert await tv.async_set_picture_mode("modeMovie") is True

    assert tv._picture_mode_id == "modeMovie"
    assert tv._picture_mode == "Movie"
