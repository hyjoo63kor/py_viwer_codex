from __future__ import annotations

from pathlib import Path

from my_app.main import IMAGE_SUFFIXES, SUPPORTED_SUFFIXES


def test_supported_suffixes_include_required_formats() -> None:
    assert {".png", ".jpg", ".jpeg", ".pdf", ".svg"} <= SUPPORTED_SUFFIXES


def test_image_suffixes_are_supported() -> None:
    assert IMAGE_SUFFIXES <= SUPPORTED_SUFFIXES


def test_rejects_unknown_suffix_by_membership() -> None:
    assert Path("sample.txt").suffix not in SUPPORTED_SUFFIXES
