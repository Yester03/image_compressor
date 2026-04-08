from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .constants import (
    DEFAULT_PERLER_BEAD_SIZE,
    DEFAULT_PERLER_BLUEPRINT,
    DEFAULT_PERLER_COLORS,
    DEFAULT_PERLER_GRID,
    DEFAULT_PERLER_LEGEND,
    DEFAULT_PERLER_SATURATION,
    DEFAULT_PERLER_SHOW_CELL_CODES,
)

@dataclass(frozen=True)
class PerlerResult:
    success: bool
    final_bytes: int
    dimensions: Tuple[int, int]
    grid_dimensions: Tuple[int, int]
    output_path: str
    palette_colors: int
    palette_used: int
    total_beads: int
    bead_size: int
    saturation: float
    blueprint: bool
    show_cell_codes: bool
    legend: bool
    reason: str

def _validate_perler_params(
    colors: int,
    grid: int,
    bead_size: int,
    saturation: float,
) -> None:
    if not (2 <= colors <= 128):
        raise ValueError("perler_colors 必须在 2 到 128 之间")
    if not (32 <= grid <= 192):
        raise ValueError("perler_grid 必须在 32 到 192 之间")
    if not (4 <= bead_size <= 128):
        raise ValueError("perler_bead_size 必须在 4 到 128 之间")
    if not (0.8 <= saturation <= 1.6):
        raise ValueError("perler_saturation 必须在 0.8 到 1.6 之间")

def _compute_perler_grid_size(size: Tuple[int, int], long_edge: int) -> Tuple[int, int]:
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("输入图片尺寸无效")

    scale = long_edge / max(width, height)
    grid_w = max(1, int(round(width * scale)))
    grid_h = max(1, int(round(height * scale)))
    return grid_w, grid_h

def _make_perler_lowres(
    base_img: Image.Image,
    colors: int,
    grid_long_edge: int,
    saturation: float,
) -> Image.Image:
    denoised = base_img.filter(ImageFilter.MedianFilter(size=3)).filter(
        ImageFilter.SMOOTH_MORE
    )
    vivid = ImageEnhance.Color(denoised).enhance(saturation)
    grid_size = _compute_perler_grid_size(vivid.size, grid_long_edge)
    low_res = vivid.resize(grid_size, Image.BOX)
    quantized = low_res.quantize(
        colors=colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).convert("RGB")
    simplified = quantized.filter(ImageFilter.ModeFilter(size=3))
    return simplified

def _render_perler_canvas(
    low_res: Image.Image,
    bead_size: int,
) -> Image.Image:
    grid_w, grid_h = low_res.size
    canvas_w = grid_w * bead_size
    canvas_h = grid_h * bead_size
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    pixel = low_res.load()
    for y in range(grid_h):
        for x in range(grid_w):
            block_color = pixel[x, y]
            left = x * bead_size
            top = y * bead_size
            right = left + bead_size - 1
            bottom = top + bead_size - 1
            draw.rectangle((left, top, right, bottom), fill=block_color)

    return canvas

def _contrast_text_color(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    luminance = rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114
    return (20, 20, 20) if luminance > 160 else (245, 245, 245)

def _collect_palette_usage(low_res: Image.Image) -> list[Tuple[Tuple[int, int, int], int]]:
    counts: dict[Tuple[int, int, int], int] = {}
    for raw_color in low_res.getdata():
        color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]))
        counts[color] = counts.get(color, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))

def _grid_label_step(size: int) -> int:
    if size <= 40:
        return 1
    if size <= 80:
        return 2
    if size <= 140:
        return 5
    return 10

def _render_perler_blueprint_canvas(
    low_res: Image.Image,
    bead_size: int,
    show_cell_codes: bool,
    show_legend: bool,
) -> Image.Image:
    grid_w, grid_h = low_res.size
    cell = max(bead_size, 8)
    group_step = 10 if max(grid_w, grid_h) > 90 else 5

    outer_pad = max(16, cell)
    axis_band = max(20, int(cell * 1.6))
    grid_left = outer_pad + axis_band
    grid_top = outer_pad + axis_band
    grid_px_w = grid_w * cell
    grid_px_h = grid_h * cell

    palette_usage = _collect_palette_usage(low_res)
    unique_colors = len(palette_usage)
    total_beads = grid_w * grid_h

    legend_h = 0
    legend_gap = max(12, int(cell * 0.9))
    if show_legend:
        swatch = max(12, int(cell * 0.95))
        item_h = swatch + 10
        item_w = max(96, int(cell * 8.5))
        content_w = axis_band + grid_px_w
        columns = max(1, content_w // item_w)
        rows = math.ceil(unique_colors / columns)
        legend_h = 30 + rows * item_h + 30

    canvas_w = outer_pad * 2 + axis_band + grid_px_w
    canvas_h = outer_pad * 2 + axis_band + grid_px_h + (legend_gap + legend_h if show_legend else 0)
    canvas = Image.new("RGB", (canvas_w, canvas_h), (246, 246, 246))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    draw.rectangle(
        (grid_left, grid_top, grid_left + grid_px_w, grid_top + grid_px_h),
        fill=(255, 255, 255),
    )

    pixels = low_res.load()
    legend_code_map: dict[Tuple[int, int, int], str] = {}
    for index, (color, _count) in enumerate(palette_usage, start=1):
        legend_code_map[color] = f"C{index:02d}"

    for y in range(grid_h):
        for x in range(grid_w):
            block_color = pixels[x, y]
            left = grid_left + x * cell
            top = grid_top + y * cell
            draw.rectangle(
                (left, top, left + cell - 1, top + cell - 1),
                fill=block_color,
            )
            if show_cell_codes and cell >= 11:
                code = legend_code_map[(int(block_color[0]), int(block_color[1]), int(block_color[2]))]
                code_box = draw.textbbox((0, 0), code, font=font)
                code_w = code_box[2] - code_box[0]
                code_h = code_box[3] - code_box[1]
                code_x = left + (cell - code_w) // 2
                code_y = top + (cell - code_h) // 2
                draw.text((code_x, code_y), code, fill=_contrast_text_color(block_color), font=font)

    thin_color = (204, 204, 204)
    thick_color = (122, 122, 122)
    for x in range(grid_w + 1):
        line_x = grid_left + x * cell
        line_color = thick_color if x % group_step == 0 else thin_color
        line_width = 2 if x % group_step == 0 else 1
        draw.line((line_x, grid_top, line_x, grid_top + grid_px_h), fill=line_color, width=line_width)

    for y in range(grid_h + 1):
        line_y = grid_top + y * cell
        line_color = thick_color if y % group_step == 0 else thin_color
        line_width = 2 if y % group_step == 0 else 1
        draw.line((grid_left, line_y, grid_left + grid_px_w, line_y), fill=line_color, width=line_width)

    draw.rectangle(
        (grid_left, grid_top, grid_left + grid_px_w, grid_top + grid_px_h),
        outline=(90, 90, 90),
        width=2,
    )

    label_color = (70, 70, 70)
    x_step = _grid_label_step(grid_w)
    y_step = _grid_label_step(grid_h)
    for x in range(1, grid_w + 1):
        if x == 1 or x == grid_w or x % x_step == 0:
            label = str(x)
            box = draw.textbbox((0, 0), label, font=font)
            label_w = box[2] - box[0]
            label_h = box[3] - box[1]
            cx = grid_left + (x - 1) * cell + cell // 2
            draw.text((cx - label_w // 2, grid_top - axis_band + (axis_band - label_h) // 2), label, fill=label_color, font=font)

    for y in range(1, grid_h + 1):
        if y == 1 or y == grid_h or y % y_step == 0:
            label = str(y)
            box = draw.textbbox((0, 0), label, font=font)
            label_w = box[2] - box[0]
            label_h = box[3] - box[1]
            cy = grid_top + (y - 1) * cell + cell // 2
            draw.text((grid_left - axis_band + (axis_band - label_w) // 2, cy - label_h // 2), label, fill=label_color, font=font)

    if show_legend:
        legend_top = grid_top + grid_px_h + legend_gap
        legend_left = outer_pad
        draw.text((legend_left, legend_top), "物料清单", fill=(40, 40, 40), font=font)

        swatch = max(12, int(cell * 0.95))
        item_h = swatch + 10
        item_w = max(96, int(cell * 8.5))
        content_w = axis_band + grid_px_w
        columns = max(1, content_w // item_w)

        items_top = legend_top + 16
        for idx, (color, count) in enumerate(palette_usage):
            row = idx // columns
            col = idx % columns
            item_x = legend_left + col * item_w
            item_y = items_top + row * item_h
            draw.rectangle(
                (item_x, item_y, item_x + swatch, item_y + swatch),
                fill=color,
                outline=(100, 100, 100),
                width=1,
            )
            label = f"{legend_code_map[color]} x{count}"
            draw.text((item_x + swatch + 6, item_y + 1), label, fill=(60, 60, 60), font=font)

        total_text = f"像素总数量: {total_beads}"
        total_box = draw.textbbox((0, 0), total_text, font=font)
        total_w = total_box[2] - total_box[0]
        total_h = total_box[3] - total_box[1]
        draw.text(
            (legend_left + content_w - total_w, legend_top + legend_h - total_h - 6),
            total_text,
            fill=(60, 60, 60),
            font=font,
        )

    return canvas

def style_image_to_perler(
    input_path: str,
    output_path: str,
    perler_colors: int = DEFAULT_PERLER_COLORS,
    perler_grid: int = DEFAULT_PERLER_GRID,
    perler_bead_size: int = DEFAULT_PERLER_BEAD_SIZE,
    perler_saturation: float = DEFAULT_PERLER_SATURATION,
    perler_blueprint: bool = DEFAULT_PERLER_BLUEPRINT,
    perler_show_cell_codes: bool = DEFAULT_PERLER_SHOW_CELL_CODES,
    perler_legend: bool = DEFAULT_PERLER_LEGEND,
) -> PerlerResult:
    _validate_perler_params(
        colors=perler_colors,
        grid=perler_grid,
        bead_size=perler_bead_size,
        saturation=perler_saturation,
    )

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"找不到输入文件: {input_path}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_file) as img:
        base_img = ImageOps.exif_transpose(img).convert("RGB")

    low_res = _make_perler_lowres(
        base_img=base_img,
        colors=perler_colors,
        grid_long_edge=perler_grid,
        saturation=perler_saturation,
    )

    palette_usage = _collect_palette_usage(low_res)
    if perler_blueprint:
        rendered = _render_perler_blueprint_canvas(
            low_res=low_res,
            bead_size=perler_bead_size,
            show_cell_codes=perler_show_cell_codes,
            show_legend=perler_legend,
        )
    else:
        rendered = _render_perler_canvas(low_res=low_res, bead_size=perler_bead_size)

    rendered.save(output_file, format="PNG", optimize=True)

    final_bytes = output_file.stat().st_size
    return PerlerResult(
        success=True,
        final_bytes=final_bytes,
        dimensions=rendered.size,
        grid_dimensions=low_res.size,
        output_path=str(output_file),
        palette_colors=perler_colors,
        palette_used=len(palette_usage),
        total_beads=low_res.size[0] * low_res.size[1],
        bead_size=perler_bead_size,
        saturation=perler_saturation,
        blueprint=perler_blueprint,
        show_cell_codes=perler_show_cell_codes,
        legend=perler_legend,
        reason="已完成拼豆风格转换。",
    )

