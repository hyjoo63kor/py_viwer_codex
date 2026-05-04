from __future__ import annotations

from pathlib import Path

from my_app.main import IMAGE_SUFFIXES, MARKDOWN_SUFFIXES, SUPPORTED_SUFFIXES, app_icon_path


def test_supported_suffixes_include_required_formats() -> None:
    assert {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".md"} <= SUPPORTED_SUFFIXES


def test_image_suffixes_are_supported() -> None:
    assert IMAGE_SUFFIXES <= SUPPORTED_SUFFIXES


def test_markdown_suffixes_are_supported() -> None:
    assert MARKDOWN_SUFFIXES <= SUPPORTED_SUFFIXES


def test_app_icon_asset_exists() -> None:
    icon_path = app_icon_path()

    assert icon_path.name == "app_icon.svg"
    assert icon_path.exists()


def test_rejects_unknown_suffix_by_membership() -> None:
    assert Path("sample.txt").suffix not in SUPPORTED_SUFFIXES
