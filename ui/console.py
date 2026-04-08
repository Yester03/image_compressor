from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Sequence, Tuple

from core.compress import CompressionResult
from core.constants import APP_NAME, APP_VERSION, APP_VERSION_LABEL
from core.perler import PerlerResult
from utils.paths import is_compressed_named


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _color_rgb(text: str, r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m{text}\033[0m"


def _gradient_text(
    text: str,
    start_rgb: Tuple[int, int, int],
    end_rgb: Tuple[int, int, int],
) -> str:
    if not text:
        return text

    visible_len = max(1, len(text) - 1)
    parts: list[str] = []
    for i, ch in enumerate(text):
        ratio = i / visible_len
        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        parts.append(_color_rgb(ch, r, g, b))
    return "".join(parts)


def _format_size_bytes(size_bytes: int) -> str:
    size_kb = math.ceil(size_bytes / 1024)
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_kb}KB / {size_mb:.2f}MB"


def _print_logo() -> None:
    lines = [
        "  ___                         ____                               ",
        " |_ _|_ __ ___   __ _  __ _ / ___|___  _ __ ___  _ __  _ __ ___ ",
        "  | || '_ ` _ \\ / _` |/ _` | |   / _ \\| '_ ` _ \\| '_ \\| '__/ _ \\",
        "  | || | | | | | (_| | (_| | |__| (_) | | | | | | |_) | | |  __/",
        " |___|_| |_| |_|\\__,_|\\__, |\\____\\___/|_| |_| |_| .__/|_|  \\___|",
        "                      |___/                      |_|             ",
    ]
    gradients = [
        ((255, 110, 80), (255, 215, 80)),
        ((255, 70, 140), (255, 160, 70)),
        ((140, 110, 255), (255, 90, 180)),
        ((70, 180, 255), (120, 255, 210)),
        ((80, 255, 130), (255, 230, 100)),
        ((120, 170, 255), (255, 130, 210)),
    ]

    for line, (start_rgb, end_rgb) in zip(lines, gradients):
        print(_gradient_text(line, start_rgb, end_rgb))

    title = f"{APP_NAME}  v{APP_VERSION} ({APP_VERSION_LABEL})"
    print(_gradient_text(title, (255, 210, 90), (255, 120, 180)))


def _display_images(
    images: Sequence[Path], base_dir: Path, current_target_kb: int
) -> None:
    print(
        f"\n发现 {len(images)} 张图片 (当前目标: {_format_size_bytes(current_target_kb * 1024)}):"
    )
    target_bytes = current_target_kb * 1024
    for idx, path in enumerate(images, start=1):
        rel = path.relative_to(base_dir)
        size_bytes = path.stat().st_size
        line = f"{idx:>3}. {rel} ({_format_size_bytes(size_bytes)})"

        if size_bytes > target_bytes:
            line = _color(line, "31")
        elif is_compressed_named(path):
            line = _color(line, "32")

        print(line)


def _display_images_basic(images: Sequence[Path], base_dir: Path) -> None:
    print(f"\n发现 {len(images)} 张图片:")
    for idx, path in enumerate(images, start=1):
        rel = path.relative_to(base_dir)
        size_bytes = path.stat().st_size
        print(f"{idx:>3}. {rel} ({_format_size_bytes(size_bytes)})")


def _print_result_line(result: CompressionResult) -> None:
    status = "OK" if result.success else "FAIL"
    width, height = result.dimensions
    print(
        f"{status} size={_format_size_bytes(result.final_bytes)} quality={result.quality} "
        f"dims={width}x{height} output={result.output_path}"
    )
    if not result.success:
        print(f"提示: {result.reason}")


def _print_perler_result_line(result: PerlerResult) -> None:
    status = "OK" if result.success else "FAIL"
    width, height = result.dimensions
    grid_w, grid_h = result.grid_dimensions
    mode = "blueprint" if result.blueprint else "classic"
    print(
        f"{status} size={_format_size_bytes(result.final_bytes)} colors={result.palette_used}/{result.palette_colors} "
        f"beads={result.total_beads} sat={result.saturation:.2f} grid={grid_w}x{grid_h} bead={result.bead_size}px "
        f"mode={mode} codes={int(result.show_cell_codes)} legend={int(result.legend)} "
        f"dims={width}x{height} output={result.output_path}"
    )
    if not result.success:
        print(f"提示: {result.reason}")


def _print_menu_help(show_examples: bool = False) -> None:
    print("\n主菜单:")
    print("  0. exit    退出程序")
    print("  1. run     开始选择并压缩图片")
    print("  2. scan    切换扫描模式（当前目录 / 递归子目录）")
    print("  3. help    显示帮助")
    print("  4. target  修改当前压缩大小")
    print("  6. style   开始选择并转换为拼豆风格")
    print("  7. dir     切换工作目录")

    if show_examples:
        print("\n常见用法:")
        print("  交互模式: 直接运行 python main.py")
        print("    - 菜单输入 1 开始压缩，回车默认当前目标")
        print("    - 菜单输入 4 修改当前目标大小")
        print("    - 选图支持输入序号/文件名，多选可用 1,2,3")
        print("  命令行模式: python main.py img/input -k 200")
        print("    - 指定输出: python main.py img/input/in.png -k 200 -o out.jpg")
        print("    - 覆盖输出: python main.py img/input/in.png -k 200 --overwrite")
        print("    - 目录批量: python main.py img/input -k 200 --recursive")
        print("  拼豆风格: python main.py img/input/in.png --mode perler")


def _clear_console() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _render_main_menu(base_dir: Path, current_target_kb: int, recursive: bool) -> None:
    _clear_console()
    _print_logo()
    print(f"工作目录: {base_dir}")
    print(f"默认目标大小: {_format_size_bytes(current_target_kb * 1024)}")
    print(f"扫描模式: {'递归子目录' if recursive else '当前目录'}")
    _print_menu_help()
