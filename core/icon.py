from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, ImageOps

from .constants import DEFAULT_ICON_SIZES


@dataclass(frozen=True)
class IconResult:
    success: bool
    final_bytes: int
    dimensions: Tuple[int, int]
    output_path: str
    icon_sizes: Tuple[int, ...]
    reason: str


def normalize_icon_sizes(icon_sizes: Iterable[int]) -> Tuple[int, ...]:
    normalized = sorted({int(size) for size in icon_sizes})
    if not normalized:
        raise ValueError("icon_sizes 不能为空")

    for size in normalized:
        if not (16 <= size <= 256):
            raise ValueError("icon_sizes 每个尺寸必须在 16 到 256 之间")

    return tuple(normalized)


def _fit_to_square_canvas(img: Image.Image, size: int) -> Image.Image:
    src_w, src_h = img.size
    scale = size / max(src_w, src_h)
    dst_w = max(1, int(round(src_w * scale)))
    dst_h = max(1, int(round(src_h * scale)))

    resized = img.resize((dst_w, dst_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset_x = (size - dst_w) // 2
    offset_y = (size - dst_h) // 2
    canvas.paste(resized, (offset_x, offset_y), resized)
    return canvas


def convert_image_to_icon(
    input_path: str,
    output_path: str,
    icon_sizes: Tuple[int, ...] = DEFAULT_ICON_SIZES,
) -> IconResult:
    normalized_sizes = normalize_icon_sizes(icon_sizes)

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"找不到输入文件: {input_path}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_file) as img:
        base_img = ImageOps.exif_transpose(img).convert("RGBA")

    max_size = max(normalized_sizes)
    icon_canvas = _fit_to_square_canvas(base_img, max_size)
    icon_canvas.save(
        output_file,
        format="ICO",
        sizes=[(size, size) for size in normalized_sizes],
    )

    final_bytes = output_file.stat().st_size
    return IconResult(
        success=True,
        final_bytes=final_bytes,
        dimensions=icon_canvas.size,
        output_path=str(output_file),
        icon_sizes=normalized_sizes,
        reason="已完成图标转换。",
    )
