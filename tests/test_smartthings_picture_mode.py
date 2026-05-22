"""Tests for SmartThings picture mode id selection."""

from custom_components.samsungtv_artmode.api.smartthings import SmartThingsTV


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
