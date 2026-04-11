from __future__ import annotations

import argparse

from core.constants import (
    APP_NAME,
    APP_VERSION,
    APP_VERSION_LABEL,
    DEFAULT_ICON_SIZES,
    DEFAULT_PERLER_BEAD_SIZE,
    DEFAULT_PERLER_BLUEPRINT,
    DEFAULT_PERLER_COLORS,
    DEFAULT_PERLER_GRID,
    DEFAULT_PERLER_LEGEND,
    DEFAULT_PERLER_SATURATION,
    DEFAULT_PERLER_SHOW_CELL_CODES,
)


def build_parser() -> argparse.ArgumentParser:
    default_icon_sizes_text = ",".join(str(size) for size in DEFAULT_ICON_SIZES)
    examples = (
        "示例:\n"
        "  python main.py img/input/in.png -k 200\n"
        "  python main.py img/input/in.jpg -k 300 -o out.jpg\n"
        "  python main.py img/input/in.png -k 150 --verbose\n"
        "  python main.py img/input/in.png --mode perler\n"
        "  python main.py img/input/in.png --mode perler --perler-blueprint --perler-legend\n"
        "  python main.py img/input --mode perler --recursive\n"
        "  python main.py img/input/in.png --mode icon\n"
        f"  python main.py img/input/in.png --mode icon --icon-sizes {default_icon_sizes_text}\n"
        "  python main.py img/input --mode icon --recursive\n"
    )
    parser = argparse.ArgumentParser(
        description="图片工具：支持 JPEG 压缩、拼豆风格转换与 ICO 图标转换。",
        epilog=examples,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} v{APP_VERSION} ({APP_VERSION_LABEL})",
    )
    parser.add_argument("input", help="输入路径：可以是图片文件或目录")
    parser.add_argument(
        "--mode",
        choices=("compress", "perler", "icon"),
        default="compress",
        help="处理模式：compress=压缩到目标体积，perler=拼豆风格转换，icon=转换为 .ico 图标",
    )
    parser.add_argument(
        "-k",
        "--target-kb",
        type=int,
        help="目标大小（KB），例如 200（仅 compress 模式使用）",
    )
    parser.add_argument(
        "--icon-sizes",
        default=default_icon_sizes_text,
        help=f"图标尺寸列表（逗号分隔，默认 {default_icon_sizes_text}，范围 16~256）",
    )
    parser.add_argument(
        "-o", "--output", help="输出路径（单图时为文件；目录模式下为输出目录）"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="允许覆盖已存在的输出文件（默认不覆盖）",
    )
    parser.add_argument("--min-quality", type=int, default=20, help=argparse.SUPPRESS)
    parser.add_argument("--max-quality", type=int, default=95, help=argparse.SUPPRESS)
    parser.add_argument(
        "--resize-step", type=float, default=0.9, help=argparse.SUPPRESS
    )
    parser.add_argument("--min-width", type=int, default=300, help=argparse.SUPPRESS)
    parser.add_argument("--min-height", type=int, default=300, help=argparse.SUPPRESS)
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="当输入为目录时，递归处理子目录",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="输出每轮压缩详情（质量/尺寸/体积）",
    )
    parser.add_argument(
        "--perler-colors",
        type=int,
        default=DEFAULT_PERLER_COLORS,
        help="拼豆调色板颜色数（默认 48，越大颜色越丰富）",
    )
    parser.add_argument(
        "--perler-grid",
        type=int,
        default=DEFAULT_PERLER_GRID,
        help="拼豆网格长边格数（默认 96，越大细节越多）",
    )
    parser.add_argument(
        "--perler-bead-size",
        type=int,
        default=DEFAULT_PERLER_BEAD_SIZE,
        help="拼豆单颗像素直径（默认 10，影响输出图尺寸）",
    )
    parser.add_argument(
        "--perler-saturation",
        type=float,
        default=DEFAULT_PERLER_SATURATION,
        help="拼豆饱和度增强系数（默认 1.15，范围 0.8~1.6，越大越鲜艳）",
    )
    parser.add_argument(
        "--perler-blueprint",
        action="store_true",
        default=DEFAULT_PERLER_BLUEPRINT,
        help="启用拼豆图纸版式（网格、坐标与底部清单）",
    )
    parser.add_argument(
        "--perler-show-cell-codes",
        action="store_true",
        default=DEFAULT_PERLER_SHOW_CELL_CODES,
        help="在每个格子中绘制色码（默认关闭）",
    )
    parser.add_argument(
        "--perler-legend",
        dest="perler_legend",
        action="store_true",
        default=DEFAULT_PERLER_LEGEND,
        help="显示底部物料清单（默认开启）",
    )
    parser.add_argument(
        "--no-perler-legend",
        dest="perler_legend",
        action="store_false",
        help="关闭底部物料清单",
    )
    return parser
