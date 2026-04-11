from __future__ import annotations

import re

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

DEFAULT_TARGET_KB = 2048

DEFAULT_PERLER_COLORS = 48

DEFAULT_PERLER_GRID = 96

DEFAULT_PERLER_BEAD_SIZE = 10

DEFAULT_PERLER_SATURATION = 1.15

DEFAULT_PERLER_BLUEPRINT = False

DEFAULT_PERLER_SHOW_CELL_CODES = False

DEFAULT_PERLER_LEGEND = True

DEFAULT_ICON_SIZES = (16, 32, 48, 64, 128, 256)

APP_NAME = "Image Compressor CLI"

APP_VERSION = "1.0.0"

APP_VERSION_LABEL = "压缩+像素风格化+图标转换"

EXIT_COMMANDS = {"exit", "quit", "q"}

COMPRESSED_NAME_RE = re.compile(r".+-compre-\d+kb(?:-\d+)?\.jpg$", re.IGNORECASE)
