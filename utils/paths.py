from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.constants import COMPRESSED_NAME_RE, IMAGE_SUFFIXES

DEFAULT_INPUT_DIR = Path("img/input")
DEFAULT_OUTPUT_DIR = Path("img/output")


def ensure_image_dirs() -> None:
    DEFAULT_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _default_output_path(
    input_file: Path,
    target_kb: int,
    output_root: Optional[Path] = None,
) -> Path:
    root = output_root or DEFAULT_OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{input_file.stem}-compre-{target_kb}kb.jpg"


def _default_perler_output_path(
    input_file: Path,
    output_root: Optional[Path] = None,
) -> Path:
    root = output_root or DEFAULT_OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{input_file.stem}-perler.png"


def _default_icon_output_path(
    input_file: Path,
    output_root: Optional[Path] = None,
) -> Path:
    root = output_root or DEFAULT_OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{input_file.stem}-icon.ico"


def _next_available_path(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path

    index = 1
    while True:
        candidate = base_path.with_name(f"{base_path.stem}-{index}{base_path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def next_output_path(
    input_file: Path,
    target_kb: int,
    output_root: Optional[Path] = None,
) -> Path:
    return _next_available_path(_default_output_path(input_file, target_kb, output_root))


def next_perler_output_path(
    input_file: Path,
    output_root: Optional[Path] = None,
) -> Path:
    return _next_available_path(_default_perler_output_path(input_file, output_root))


def next_icon_output_path(
    input_file: Path,
    output_root: Optional[Path] = None,
) -> Path:
    return _next_available_path(_default_icon_output_path(input_file, output_root))


def list_images(recursive: bool, base_dir: Optional[Path] = None) -> list[Path]:
    root = base_dir or DEFAULT_INPUT_DIR
    if not root.exists():
        return []

    pattern = "**/*" if recursive else "*"
    images = [
        p
        for p in root.glob(pattern)
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    ]
    return sorted(images, key=lambda p: str(p.relative_to(root)).lower())


def is_compressed_named(path: Path) -> bool:
    return COMPRESSED_NAME_RE.fullmatch(path.name) is not None
