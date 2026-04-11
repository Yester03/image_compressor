from __future__ import annotations

import math
from pathlib import Path
from typing import Optional, Sequence, Tuple

from core.compress import compress_image_to_target_kb
from core.constants import (
    DEFAULT_ICON_SIZES,
    DEFAULT_PERLER_BEAD_SIZE,
    DEFAULT_PERLER_BLUEPRINT,
    DEFAULT_PERLER_COLORS,
    DEFAULT_PERLER_GRID,
    DEFAULT_PERLER_LEGEND,
    DEFAULT_PERLER_SATURATION,
    DEFAULT_PERLER_SHOW_CELL_CODES,
    DEFAULT_TARGET_KB,
    EXIT_COMMANDS,
    IMAGE_SUFFIXES,
)
from core.icon import convert_image_to_icon, normalize_icon_sizes
from core.perler import style_image_to_perler, _validate_perler_params
from ui.console import (
    _clear_console,
    _color,
    _display_images,
    _display_images_basic,
    _format_size_bytes,
    _print_icon_result_line,
    _print_logo,
    _print_menu_help,
    _print_perler_result_line,
    _print_result_line,
    _render_main_menu,
)
from utils.paths import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    _next_available_path,
    ensure_image_dirs,
    list_images,
    next_icon_output_path,
    next_output_path,
    next_perler_output_path,
)


def parse_menu_command(text: str) -> str:
    normalized = text.strip().lower()
    aliases = {
        "": "help",
        "0": "exit",
        "1": "run",
        "2": "scan",
        "3": "help",
        "4": "target",
        "5": "icon",
        "6": "style",
        "7": "dir",
        "h": "help",
        "?": "help",
        "s": "scan",
        "r": "run",
        "t": "target",
        "i": "icon",
        "d": "dir",
        "p": "style",
        "e": "exit",
    }
    return aliases.get(normalized, normalized)


def parse_target_kb(text: str, default_kb: int = DEFAULT_TARGET_KB) -> int:
    raw = text.strip().lower().replace(" ", "")
    if not raw:
        return default_kb

    unit = "kb"
    number_part = raw
    if raw.endswith("mb"):
        unit = "mb"
        number_part = raw[:-2]
    elif raw.endswith("m"):
        unit = "mb"
        number_part = raw[:-1]
    elif raw.endswith("kb"):
        unit = "kb"
        number_part = raw[:-2]
    elif raw.endswith("k"):
        unit = "kb"
        number_part = raw[:-1]

    if not number_part:
        raise ValueError("目标大小不能为空")

    number = float(number_part)
    if number <= 0:
        raise ValueError("目标大小必须大于 0")

    kb = math.ceil(number * 1024) if unit == "mb" else math.ceil(number)
    if kb <= 0:
        raise ValueError("目标大小必须大于 0")
    return kb


def parse_icon_sizes(text: str, default_sizes: Tuple[int, ...] = DEFAULT_ICON_SIZES) -> Tuple[int, ...]:
    raw = text.strip().replace(" ", "")
    if not raw:
        return default_sizes

    parts = [part for part in raw.split(",") if part]
    if not parts:
        raise ValueError("icon 尺寸不能为空，请输入逗号分隔整数，例如 16,32,48,64,128,256")

    values: list[int] = []
    for part in parts:
        try:
            values.append(int(part))
        except ValueError as exc:
            raise ValueError(f"icon 尺寸包含非整数值: {part}") from exc

    return normalize_icon_sizes(values)


def _prompt_yes_no(prompt: str, default: bool) -> Optional[bool]:
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt}（{hint}，exit退出）: ").strip().lower()
        if raw in EXIT_COMMANDS:
            return None
        if not raw:
            return default
        if raw in {"y", "yes", "1"}:
            return True
        if raw in {"n", "no", "0"}:
            return False
        print("输入无效: 请输入 y 或 n。")


def select_images(
    images: Sequence[Path], user_input: str, base_dir: Optional[Path] = None
) -> Optional[list[Path]]:
    text = user_input.strip()
    if not text:
        return None

    root = base_dir or Path.cwd()
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return None

    selected: list[Path] = []
    seen: set[Path] = set()

    for part in parts:
        candidate: Optional[Path] = None

        if part.isdigit():
            index = int(part)
            if 1 <= index <= len(images):
                candidate = images[index - 1]
        else:
            lowered = part.lower()
            matches = [
                p
                for p in images
                if p.name.lower() == lowered
                or str(p.relative_to(root)).lower() == lowered
            ]
            if len(matches) == 1:
                candidate = matches[0]

        if candidate is None:
            return None
        if candidate not in seen:
            selected.append(candidate)
            seen.add(candidate)

    return selected


def _interactive_run(base_dir: Path, recursive: bool, current_target_kb: int) -> bool:
    images = list_images(recursive=recursive, base_dir=base_dir)
    if not images:
        mode = "递归子目录" if recursive else "当前目录"
        print(f"\n未找到可压缩图片（模式: {mode}）。")
        return False

    _display_images(images, base_dir, current_target_kb)

    while True:
        raw = input(
            "\n选择图片（序号/文件名，可多选如 1,2,3，back返回，exit退出）: "
        ).strip()
        cmd = raw.lower()
        if cmd in EXIT_COMMANDS:
            return True
        if cmd == "back":
            return False

        selected_images = select_images(images, raw, base_dir=base_dir)
        if selected_images is None:
            print("输入无效，请输入正确序号/文件名，或使用逗号多选（例如 1,2,3）。")
            continue

        while True:
            default_target_text = _format_size_bytes(current_target_kb * 1024)
            target_raw = input(
                f"目标大小（默认 {default_target_text}，可填 1500 / 1500kb / 1.8mb，back返回）: "
            ).strip()
            target_cmd = target_raw.lower()
            if target_cmd in EXIT_COMMANDS:
                return True
            if target_cmd == "back":
                break

            try:
                target_kb = parse_target_kb(target_raw, default_kb=current_target_kb)
            except ValueError as exc:
                print(f"输入无效: {exc}")
                continue

            print(f"\n开始批量压缩，共 {len(selected_images)} 张...")
            for idx, image in enumerate(selected_images, start=1):
                output_path = next_output_path(image, target_kb, output_root=DEFAULT_OUTPUT_DIR)
                try:
                    result = compress_image_to_target_kb(
                        input_path=str(image),
                        output_path=str(output_path),
                        target_kb=target_kb,
                    )
                except Exception as exc:
                    print(
                        f"[{idx}/{len(selected_images)}] {image.name} 压缩失败: {exc}"
                    )
                    continue

                print(f"[{idx}/{len(selected_images)}] {image.name}")
                _print_result_line(result)
            return False


def _interactive_style(
    base_dir: Path,
    recursive: bool,
    perler_colors: int = DEFAULT_PERLER_COLORS,
    perler_grid: int = DEFAULT_PERLER_GRID,
    perler_bead_size: int = DEFAULT_PERLER_BEAD_SIZE,
    perler_saturation: float = DEFAULT_PERLER_SATURATION,
) -> bool:
    images = list_images(recursive=recursive, base_dir=base_dir)
    if not images:
        mode = "递归子目录" if recursive else "当前目录"
        print(f"\n未找到可转换图片（模式: {mode}）。")
        return False

    _display_images_basic(images, base_dir)

    while True:
        raw = input(
            "\n选择图片（序号/文件名，可多选如 1,2,3，back返回，exit退出）: "
        ).strip()
        cmd = raw.lower()
        if cmd in EXIT_COMMANDS:
            return True
        if cmd == "back":
            return False

        selected_images = select_images(images, raw, base_dir=base_dir)
        if selected_images is None:
            print("输入无效，请输入正确序号/文件名，或使用逗号多选（例如 1,2,3）。")
            continue

        print("\n配置拼豆参数（直接回车使用默认值）:")
        should_exit, perler_params = _prompt_perler_params(
            default_colors=perler_colors,
            default_grid=perler_grid,
            default_bead_size=perler_bead_size,
            default_saturation=perler_saturation,
            allow_back=True,
        )
        if should_exit:
            return True
        if perler_params is None:
            continue
        colors, grid, bead_size, saturation = perler_params

        use_blueprint = _prompt_yes_no("启用图纸版式（网格+坐标+清单）", DEFAULT_PERLER_BLUEPRINT)
        if use_blueprint is None:
            return True
        use_cell_codes = _prompt_yes_no("在格子内显示色码", DEFAULT_PERLER_SHOW_CELL_CODES)
        if use_cell_codes is None:
            return True
        use_legend = _prompt_yes_no("显示底部物料清单", DEFAULT_PERLER_LEGEND)
        if use_legend is None:
            return True

        print(
            f"\n开始拼豆风格转换，共 {len(selected_images)} 张..."
            f" (colors={colors}, sat={saturation:.2f}, "
            f"grid={grid}, bead={bead_size}px, blueprint={int(use_blueprint)}, "
            f"codes={int(use_cell_codes)}, legend={int(use_legend)})"
        )
        for idx, image in enumerate(selected_images, start=1):
            output_path = next_perler_output_path(image, output_root=DEFAULT_OUTPUT_DIR)
            try:
                result = style_image_to_perler(
                    input_path=str(image),
                    output_path=str(output_path),
                    perler_colors=colors,
                    perler_grid=grid,
                    perler_bead_size=bead_size,
                    perler_saturation=saturation,
                    perler_blueprint=use_blueprint,
                    perler_show_cell_codes=use_cell_codes,
                    perler_legend=use_legend,
                )
            except Exception as exc:
                print(f"[{idx}/{len(selected_images)}] {image.name} 转换失败: {exc}")
                continue

            print(f"[{idx}/{len(selected_images)}] {image.name}")
            _print_perler_result_line(result)
        return False


def _prompt_icon_sizes(
    default_sizes: Tuple[int, ...] = DEFAULT_ICON_SIZES,
    allow_back: bool = True,
) -> Tuple[bool, Optional[Tuple[int, ...]]]:
    default_text = ",".join(str(size) for size in default_sizes)
    while True:
        raw = input(
            f"icon-sizes（默认 {default_text}，范围 16~256，逗号分隔，back返回，exit退出）: "
        ).strip()
        cmd = raw.lower()
        if cmd in EXIT_COMMANDS:
            return True, None
        if allow_back and cmd == "back":
            return False, None

        try:
            sizes = parse_icon_sizes(raw, default_sizes=default_sizes)
        except ValueError as exc:
            print(f"输入无效: {exc}")
            continue

        return False, sizes


def _interactive_icon(
    base_dir: Path,
    recursive: bool,
    default_icon_sizes: Tuple[int, ...] = DEFAULT_ICON_SIZES,
) -> bool:
    images = list_images(recursive=recursive, base_dir=base_dir)
    if not images:
        mode = "递归子目录" if recursive else "当前目录"
        print(f"\n未找到可转换图片（模式: {mode}）。")
        return False

    _display_images_basic(images, base_dir)

    while True:
        raw = input(
            "\n选择图片（序号/文件名，可多选如 1,2,3，back返回，exit退出）: "
        ).strip()
        cmd = raw.lower()
        if cmd in EXIT_COMMANDS:
            return True
        if cmd == "back":
            return False

        selected_images = select_images(images, raw, base_dir=base_dir)
        if selected_images is None:
            print("输入无效，请输入正确序号/文件名，或使用逗号多选（例如 1,2,3）。")
            continue

        should_exit, icon_sizes = _prompt_icon_sizes(default_sizes=default_icon_sizes)
        if should_exit:
            return True
        if icon_sizes is None:
            continue

        print(
            f"\n开始图标转换，共 {len(selected_images)} 张..."
            f" (sizes={','.join(str(size) for size in icon_sizes)})"
        )
        for idx, image in enumerate(selected_images, start=1):
            output_path = next_icon_output_path(image, output_root=DEFAULT_OUTPUT_DIR)
            try:
                result = convert_image_to_icon(
                    input_path=str(image),
                    output_path=str(output_path),
                    icon_sizes=icon_sizes,
                )
            except Exception as exc:
                print(f"[{idx}/{len(selected_images)}] {image.name} 转换失败: {exc}")
                continue

            print(f"[{idx}/{len(selected_images)}] {image.name}")
            _print_icon_result_line(result)
        return False


def _prompt_perler_params(
    default_colors: int = DEFAULT_PERLER_COLORS,
    default_grid: int = DEFAULT_PERLER_GRID,
    default_bead_size: int = DEFAULT_PERLER_BEAD_SIZE,
    default_saturation: float = DEFAULT_PERLER_SATURATION,
    allow_back: bool = True,
) -> Tuple[bool, Optional[Tuple[int, int, int, float]]]:
    print("参数说明:")
    print("  - colors: 颜色数，越大越丰富鲜艳，但也更复杂。")
    print("  - grid: 长边拼豆数（像素个数），越大细节越多，图会更大。")
    print("  - bead-size: 每颗拼豆显示直径，影响输出图尺寸，不改变豆子数量。")
    print("  - saturation: 饱和度系数，越大颜色越鲜艳。")

    while True:
        colors_raw = input(
            f"colors（默认 {default_colors}，范围 2~128；影响颜色丰富度，back返回，exit退出）: "
        ).strip()
        colors_cmd = colors_raw.lower()
        if colors_cmd in EXIT_COMMANDS:
            return True, None
        if allow_back and colors_cmd == "back":
            return False, None
        if not colors_raw:
            colors = default_colors
        else:
            try:
                colors = int(colors_raw)
            except ValueError:
                print("输入无效: colors 必须是整数")
                continue

        grid_raw = input(
            f"grid（默认 {default_grid}，长边拼豆数，范围 32~192；影响细节与豆子数量，back返回，exit退出）: "
        ).strip()
        grid_cmd = grid_raw.lower()
        if grid_cmd in EXIT_COMMANDS:
            return True, None
        if allow_back and grid_cmd == "back":
            return False, None
        if not grid_raw:
            grid = default_grid
        else:
            try:
                grid = int(grid_raw)
            except ValueError:
                print("输入无效: grid 必须是整数")
                continue

        bead_raw = input(
            f"bead-size（默认 {default_bead_size}，范围 4~128；影响每颗豆显示大小，back返回，exit退出）: "
        ).strip()
        bead_cmd = bead_raw.lower()
        if bead_cmd in EXIT_COMMANDS:
            return True, None
        if allow_back and bead_cmd == "back":
            return False, None
        if not bead_raw:
            bead_size = default_bead_size
        else:
            try:
                bead_size = int(bead_raw)
            except ValueError:
                print("输入无效: bead-size 必须是整数")
                continue

        saturation_raw = input(
            f"saturation（默认 {default_saturation:.2f}，范围 0.8~1.6；影响鲜艳程度，back返回，exit退出）: "
        ).strip()
        saturation_cmd = saturation_raw.lower()
        if saturation_cmd in EXIT_COMMANDS:
            return True, None
        if allow_back and saturation_cmd == "back":
            return False, None
        if not saturation_raw:
            saturation = default_saturation
        else:
            try:
                saturation = float(saturation_raw)
            except ValueError:
                print("输入无效: saturation 必须是数字")
                continue

        try:
            _validate_perler_params(
                colors=colors,
                grid=grid,
                bead_size=bead_size,
                saturation=saturation,
            )
        except ValueError as exc:
            print(f"输入无效: {exc}")
            continue

        return False, (colors, grid, bead_size, saturation)


def _configure_target_kb(current_target_kb: int) -> Tuple[bool, int]:
    while True:
        raw = input(
            f"输入新的默认目标大小（当前 {_format_size_bytes(current_target_kb * 1024)}，例如 1500kb / 1.8mb，back返回）: "
        ).strip()
        cmd = raw.lower()
        if cmd in EXIT_COMMANDS:
            return True, current_target_kb
        if cmd == "back":
            return False, current_target_kb

        try:
            new_target_kb = parse_target_kb(raw, default_kb=current_target_kb)
        except ValueError as exc:
            print(f"输入无效: {exc}")
            continue

        print(f"当前默认压缩大小已更新为: {_format_size_bytes(new_target_kb * 1024)}")
        return False, new_target_kb


def _dir_has_image_files(dir_path: Path) -> bool:
    try:
        for item in dir_path.iterdir():
            if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES:
                return True
    except OSError:
        return False
    return False


def _directory_choices(base_dir: Path) -> list[Tuple[str, Path]]:
    entries: list[Tuple[str, Path]] = []

    parent = base_dir.parent
    if parent != base_dir and parent.exists() and parent.is_dir():
        entries.append(("[父目录]", parent))

    children = sorted(
        (p for p in base_dir.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    for child in children:
        entries.append((child.name, child))

    return entries


def _configure_base_dir(current_base_dir: Path) -> Tuple[bool, Path]:
    entries = _directory_choices(current_base_dir)

    print(f"\n目录导航（当前: {current_base_dir}）")
    if not entries:
        print("  当前目录没有父目录或子目录，可直接输入路径。")
    else:
        for idx, (label, target) in enumerate(entries, start=1):
            display_label = _color(label, "31") if _dir_has_image_files(target) else label
            print(f"  {idx}. {display_label} -> {target}")

    while True:
        raw = input("输入编号切换目录（如 1，back返回，exit退出）: ").strip()
        cmd = raw.lower()
        if cmd in EXIT_COMMANDS:
            return True, current_base_dir
        if cmd == "back":
            return False, current_base_dir
        if not raw:
            print("输入无效: 请输入编号或路径")
            continue

        token_text = raw.replace(" ", "")
        if token_text.isdigit():
            index = int(token_text)
            if 1 <= index <= len(entries):
                selected = entries[index - 1][1]
                print(f"工作目录已切换为: {selected}")
                return False, selected
            print("输入无效: 编号超出范围")
            continue

        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (current_base_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists():
            print(f"输入无效: 目录不存在 -> {candidate}")
            continue
        if not candidate.is_dir():
            print(f"输入无效: 不是目录 -> {candidate}")
            continue

        print(f"工作目录已切换为: {candidate}")
        return False, candidate


def interactive_menu() -> int:
    ensure_image_dirs()
    base_dir = DEFAULT_INPUT_DIR.resolve()
    recursive = False
    current_target_kb = DEFAULT_TARGET_KB

    while True:
        _render_main_menu(
            base_dir=base_dir,
            current_target_kb=current_target_kb,
            recursive=recursive,
        )

        raw = input("\nmenu(0-7)> ")
        cmd = parse_menu_command(raw)

        if cmd in EXIT_COMMANDS:
            print("已退出。")
            return 0
        if cmd == "help":
            _clear_console()
            _print_logo()
            _print_menu_help(show_examples=True)
            input("\n按回车返回主菜单...")
            continue
        if cmd == "scan":
            recursive = not recursive
            continue
        if cmd == "target":
            should_exit, current_target_kb = _configure_target_kb(current_target_kb)
            if should_exit:
                print("已退出。")
                return 0
            continue
        if cmd == "dir":
            should_exit, base_dir = _configure_base_dir(base_dir)
            if should_exit:
                print("已退出。")
                return 0
            continue
        if cmd == "run":
            should_exit = _interactive_run(
                base_dir=base_dir,
                recursive=recursive,
                current_target_kb=current_target_kb,
            )
            if should_exit:
                print("已退出。")
                return 0
            continue

        if cmd == "icon":
            should_exit = _interactive_icon(
                base_dir=base_dir,
                recursive=recursive,
                default_icon_sizes=DEFAULT_ICON_SIZES,
            )
            if should_exit:
                print("已退出。")
                return 0
            continue

        if cmd == "style":
            should_exit = _interactive_style(
                base_dir=base_dir,
                recursive=recursive,
                perler_colors=DEFAULT_PERLER_COLORS,
                perler_grid=DEFAULT_PERLER_GRID,
                perler_bead_size=DEFAULT_PERLER_BEAD_SIZE,
                perler_saturation=DEFAULT_PERLER_SATURATION,
            )
            if should_exit:
                print("已退出。")
                return 0
            continue

        print("未知命令，请输入 0/1/2/3/4/5/6/7 或 run/scan/help/target/icon/style/dir/exit")
        input("按回车返回主菜单...")


def _is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES


def _should_use_drag_drop_mode(args: Sequence[str]) -> bool:
    if not args:
        return False
    if any(arg.startswith("-") for arg in args):
        return False

    for arg in args:
        path = Path(arg)
        if not path.exists() or not _is_image_file(path):
            return False
    return True


def _run_drag_drop_mode(paths: Sequence[str], target_kb: int = DEFAULT_TARGET_KB) -> int:
    ensure_image_dirs()
    output_dir = DEFAULT_OUTPUT_DIR
    images = [Path(p) for p in paths]

    print("\n拖拽模式：请选择处理方式")
    print("  1. compress  压缩到目标体积")
    print("  2. perler    转换为拼豆风格")
    print("  3. icon      转换为 ICO 图标")
    selected_mode = "compress"
    perler_colors = DEFAULT_PERLER_COLORS
    perler_grid = DEFAULT_PERLER_GRID
    perler_bead_size = DEFAULT_PERLER_BEAD_SIZE
    perler_saturation = DEFAULT_PERLER_SATURATION
    perler_blueprint = DEFAULT_PERLER_BLUEPRINT
    perler_show_cell_codes = DEFAULT_PERLER_SHOW_CELL_CODES
    perler_legend = DEFAULT_PERLER_LEGEND
    icon_sizes = DEFAULT_ICON_SIZES

    while True:
        raw = input("mode(1/2/3，默认1，exit退出)> ").strip().lower()
        if raw in EXIT_COMMANDS:
            print("已退出。")
            return 0
        if raw in {"", "1", "compress", "c"}:
            selected_mode = "compress"
            break
        if raw in {"2", "perler", "p", "style"}:
            selected_mode = "perler"
            print("\n配置拼豆参数（直接回车使用默认值，back返回模式选择）:")
            should_exit, perler_params = _prompt_perler_params(
                default_colors=DEFAULT_PERLER_COLORS,
                default_grid=DEFAULT_PERLER_GRID,
                default_bead_size=DEFAULT_PERLER_BEAD_SIZE,
                default_saturation=DEFAULT_PERLER_SATURATION,
                allow_back=True,
            )
            if should_exit:
                print("已退出。")
                return 0
            if perler_params is None:
                continue
            perler_colors, perler_grid, perler_bead_size, perler_saturation = (
                perler_params
            )
            maybe_blueprint = _prompt_yes_no("启用图纸版式（网格+坐标+清单）", DEFAULT_PERLER_BLUEPRINT)
            if maybe_blueprint is None:
                print("已退出。")
                return 0
            perler_blueprint = maybe_blueprint
            maybe_codes = _prompt_yes_no("在格子内显示色码", DEFAULT_PERLER_SHOW_CELL_CODES)
            if maybe_codes is None:
                print("已退出。")
                return 0
            perler_show_cell_codes = maybe_codes
            maybe_legend = _prompt_yes_no("显示底部物料清单", DEFAULT_PERLER_LEGEND)
            if maybe_legend is None:
                print("已退出。")
                return 0
            perler_legend = maybe_legend
            break
        if raw in {"3", "icon", "ico", "i"}:
            selected_mode = "icon"
            should_exit, maybe_sizes = _prompt_icon_sizes(
                default_sizes=DEFAULT_ICON_SIZES,
                allow_back=True,
            )
            if should_exit:
                print("已退出。")
                return 0
            if maybe_sizes is None:
                continue
            icon_sizes = maybe_sizes
            break
        print("输入无效，请输入 1、2 或 3。")

    if selected_mode == "compress":
        print(
            f"拖拽模式：开始压缩，共 {len(images)} 张，输出目录: {output_dir}，目标大小: {_format_size_bytes(target_kb * 1024)}"
        )
    elif selected_mode == "perler":
        print(
            f"拖拽模式：开始拼豆风格转换，共 {len(images)} 张，输出目录: {output_dir}，"
            f"colors={perler_colors}, sat={perler_saturation:.2f}, "
            f"grid={perler_grid}, bead={perler_bead_size}px, blueprint={int(perler_blueprint)}, "
            f"codes={int(perler_show_cell_codes)}, legend={int(perler_legend)}"
        )
    else:
        print(
            f"拖拽模式：开始图标转换，共 {len(images)} 张，输出目录: {output_dir}，"
            f"sizes={','.join(str(size) for size in icon_sizes)}"
        )

    failed = 0
    for idx, image in enumerate(images, start=1):
        if selected_mode == "compress":
            default_output = output_dir / f"{image.stem}-compre-{target_kb}kb.jpg"
        elif selected_mode == "perler":
            default_output = output_dir / f"{image.stem}-perler.png"
        else:
            default_output = output_dir / f"{image.stem}-icon.ico"
        output_file = _next_available_path(default_output)

        if selected_mode == "compress":
            try:
                result = compress_image_to_target_kb(
                    input_path=str(image),
                    output_path=str(output_file),
                    target_kb=target_kb,
                )
            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(images)}] {image} 压缩失败: {exc}")
                continue

            print(f"[{idx}/{len(images)}] {image}")
            _print_result_line(result)
            if not result.success:
                failed += 1
            continue

        if selected_mode == "perler":
            try:
                perler_result = style_image_to_perler(
                    input_path=str(image),
                    output_path=str(output_file),
                    perler_colors=perler_colors,
                    perler_grid=perler_grid,
                    perler_bead_size=perler_bead_size,
                    perler_saturation=perler_saturation,
                    perler_blueprint=perler_blueprint,
                    perler_show_cell_codes=perler_show_cell_codes,
                    perler_legend=perler_legend,
                )
            except Exception as exc:
                failed += 1
                print(f"[{idx}/{len(images)}] {image} 转换失败: {exc}")
                continue

            print(f"[{idx}/{len(images)}] {image}")
            _print_perler_result_line(perler_result)
            if not perler_result.success:
                failed += 1
            continue

        try:
            icon_result = convert_image_to_icon(
                input_path=str(image),
                output_path=str(output_file),
                icon_sizes=icon_sizes,
            )
        except Exception as exc:
            failed += 1
            print(f"[{idx}/{len(images)}] {image} 转换失败: {exc}")
            continue

        print(f"[{idx}/{len(images)}] {image}")
        _print_icon_result_line(icon_result)
        if not icon_result.success:
            failed += 1

    return 0 if failed == 0 else 1
