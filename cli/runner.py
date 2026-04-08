from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

from cli.parser import build_parser
from core.compress import compress_image_to_target_kb
from core.constants import DEFAULT_TARGET_KB
from core.perler import style_image_to_perler
from ui.console import _format_size_bytes, _print_perler_result_line, _print_result_line
from ui.interactive import (
    _run_drag_drop_mode,
    _should_use_drag_drop_mode,
    interactive_menu,
)
from utils.paths import (
    DEFAULT_OUTPUT_DIR,
    _default_output_path,
    _default_perler_output_path,
    _next_available_path,
    ensure_image_dirs,
    list_images,
)


def _run_cli(argv: Sequence[str]) -> int:
    ensure_image_dirs()
    parser = build_parser()
    args = parser.parse_args(list(argv))
    mode = args.mode

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入路径不存在: {input_path}", file=sys.stderr)
        return 2

    if mode == "compress" and args.target_kb is None:
        print("错误: compress 模式必须指定 -k/--target-kb。", file=sys.stderr)
        return 2
    if mode == "perler" and args.target_kb is not None:
        print("提示: perler 模式下 --target-kb 会被忽略。", file=sys.stderr)

    if input_path.is_file():
        if mode == "compress":
            assert args.target_kb is not None
            output_file = (
                Path(args.output)
                if args.output
                else _default_output_path(input_path, args.target_kb, output_root=DEFAULT_OUTPUT_DIR)
            )
        else:
            output_file = (
                Path(args.output)
                if args.output
                else _default_perler_output_path(input_path, output_root=DEFAULT_OUTPUT_DIR)
            )

        if output_file.exists() and not args.overwrite:
            print(
                f"错误: 输出文件已存在: {output_file}\n"
                "使用 --overwrite 允许覆盖，或通过 -o 指定新路径。",
                file=sys.stderr,
            )
            return 2

        if mode == "compress":
            assert args.target_kb is not None
            try:
                result = compress_image_to_target_kb(
                    input_path=str(input_path),
                    output_path=str(output_file),
                    target_kb=args.target_kb,
                    min_quality=args.min_quality,
                    max_quality=args.max_quality,
                    resize_step=args.resize_step,
                    min_width=args.min_width,
                    min_height=args.min_height,
                )
            except Exception as exc:
                print(f"错误: {exc}", file=sys.stderr)
                return 2

            _print_result_line(result)
            if args.verbose and result.steps:
                for step in result.steps:
                    w, h = step.dimensions
                    print(
                        f"  round#{step.round_index} q={step.quality} "
                        f"size={_format_size_bytes(step.size_bytes)} dims={w}x{h}"
                    )
            return 0 if result.success else 1

        try:
            result = style_image_to_perler(
                input_path=str(input_path),
                output_path=str(output_file),
                perler_colors=args.perler_colors,
                perler_grid=args.perler_grid,
                perler_bead_size=args.perler_bead_size,
                perler_saturation=args.perler_saturation,
                perler_blueprint=args.perler_blueprint,
                perler_show_cell_codes=args.perler_show_cell_codes,
                perler_legend=args.perler_legend,
            )
        except Exception as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 2

        _print_perler_result_line(result)
        return 0 if result.success else 1

    if not input_path.is_dir():
        print(f"错误: 输入路径不是有效文件或目录: {input_path}", file=sys.stderr)
        return 2

    images = list_images(recursive=args.recursive, base_dir=input_path)
    if not images:
        print("错误: 目录中没有可处理图片。", file=sys.stderr)
        return 2

    output_root: Optional[Path] = DEFAULT_OUTPUT_DIR
    if args.output:
        output_root = Path(args.output)
        if output_root.exists() and not output_root.is_dir():
            print(f"错误: 目录批量模式下 -o 必须是输出目录: {output_root}", file=sys.stderr)
            return 2
    output_root.mkdir(parents=True, exist_ok=True)

    if mode == "compress":
        print(f"开始批量压缩，共 {len(images)} 张...")
    else:
        print(
            f"开始批量拼豆风格转换，共 {len(images)} 张..."
            f" (colors={args.perler_colors}, sat={args.perler_saturation:.2f}, "
            f"grid={args.perler_grid}, bead={args.perler_bead_size}px, "
            f"blueprint={int(args.perler_blueprint)}, codes={int(args.perler_show_cell_codes)}, "
            f"legend={int(args.perler_legend)})"
        )

    failed = 0
    for idx, image in enumerate(images, start=1):
        relative = image.relative_to(input_path)
        target_dir = output_root / relative.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        if mode == "compress":
            assert args.target_kb is not None
            default_output = target_dir / f"{image.stem}-compre-{args.target_kb}kb.jpg"
        else:
            default_output = target_dir / f"{image.stem}-perler.png"

        output_file = (
            default_output if args.overwrite else _next_available_path(default_output)
        )

        if mode == "compress":
            assert args.target_kb is not None
            try:
                result = compress_image_to_target_kb(
                    input_path=str(image),
                    output_path=str(output_file),
                    target_kb=args.target_kb,
                    min_quality=args.min_quality,
                    max_quality=args.max_quality,
                    resize_step=args.resize_step,
                    min_width=args.min_width,
                    min_height=args.min_height,
                )
            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(images)}] {image} 压缩失败: {exc}")
                continue

            print(f"[{idx}/{len(images)}] {image}")
            _print_result_line(result)
            if not result.success:
                failed += 1

            if args.verbose and result.steps:
                for step in result.steps:
                    w, h = step.dimensions
                    print(
                        f"  round#{step.round_index} q={step.quality} "
                        f"size={_format_size_bytes(step.size_bytes)} dims={w}x{h}"
                    )
            continue

        try:
            perler_result = style_image_to_perler(
                input_path=str(image),
                output_path=str(output_file),
                perler_colors=args.perler_colors,
                perler_grid=args.perler_grid,
                perler_bead_size=args.perler_bead_size,
                perler_saturation=args.perler_saturation,
                perler_blueprint=args.perler_blueprint,
                perler_show_cell_codes=args.perler_show_cell_codes,
                perler_legend=args.perler_legend,
            )
        except Exception as exc:
            failed += 1
            print(f"[{idx}/{len(images)}] {image} 转换失败: {exc}")
            continue

        print(f"[{idx}/{len(images)}] {image}")
        _print_perler_result_line(perler_result)
        if not perler_result.success:
            failed += 1

    return 0 if failed == 0 else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if not args:
        return interactive_menu()

    if _should_use_drag_drop_mode(args):
        return _run_drag_drop_mode(args, target_kb=DEFAULT_TARGET_KB)

    return _run_cli(args)
