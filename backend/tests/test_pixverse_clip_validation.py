from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.endpoints import (
    _clip_matches_aspect_ratio,
    _natural_media_sort_key,
    _validate_pixverse_clip_paths,
)


def test_natural_media_sort_key_orders_numeric_shots() -> None:
    names = [Path("10_final.mp4"), Path("2_mid.mp4"), Path("01_intro.mp4")]
    ordered = sorted(names, key=_natural_media_sort_key)
    assert [item.name for item in ordered] == ["01_intro.mp4", "2_mid.mp4", "10_final.mp4"]


def test_clip_matches_aspect_ratio_accepts_vertical_video() -> None:
    assert _clip_matches_aspect_ratio(1080, 1920, "9:16")
    assert not _clip_matches_aspect_ratio(1920, 1080, "9:16")


def test_validate_pixverse_clip_paths_rejects_wrong_clip_count() -> None:
    with pytest.raises(HTTPException) as exc:
        _validate_pixverse_clip_paths(["a.mp4", "b.mp4", "c.mp4"], aspect_ratio="9:16")
    assert exc.value.status_code == 400
    assert "4-8 clips" in str(exc.value.detail)
