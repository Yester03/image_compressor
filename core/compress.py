from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps

@dataclass(frozen=True)
class CompressionStep:
    round_index: int
    quality: int
    size_bytes: int
    dimensions: Tuple[int, int]

@dataclass(frozen=True)
class CompressionResult:
    success: bool
    final_kb: int
    quality: int
    dimensions: Tuple[int, int]
    output_path: str
    final_bytes: int
    reason: str
    steps: Tuple[CompressionStep, ...]

@dataclass(frozen=True)
class _Candidate:
    data: bytes
    quality: int
    size_bytes: int
    dimensions: Tuple[int, int]

def _validate_params(
    target_kb: int,
    min_quality: int,
    max_quality: int,
    resize_step: float,
    min_width: int,
    min_height: int,
) -> None:
    if target_kb <= 0:
        raise ValueError("target_kb 必须大于 0")
    if not (1 <= min_quality <= max_quality <= 95):
        raise ValueError("quality 范围必须满足 1 <= min_quality <= max_quality <= 95")
    if not (0 < resize_step < 1):
        raise ValueError("resize_step 必须在 0 和 1 之间（不含端点）")
    if min_width < 1 or min_height < 1:
        raise ValueError("min_width / min_height 必须大于等于 1")

def _is_better_candidate(
    current: _Candidate,
    best: Optional[_Candidate],
    target_bytes: int,
) -> bool:
    if best is None:
        return True

    current_under = current.size_bytes <= target_bytes
    best_under = best.size_bytes <= target_bytes

    if current_under and not best_under:
        return True
    if not current_under and best_under:
        return False

    if current_under and best_under:
        return (target_bytes - current.size_bytes) < (target_bytes - best.size_bytes)
    return (current.size_bytes - target_bytes) < (best.size_bytes - target_bytes)

def compress_image_to_target_kb(
    input_path: str,
    output_path: str,
    target_kb: int,
    min_quality: int = 20,
    max_quality: int = 95,
    resize_step: float = 0.9,
    min_width: int = 300,
    min_height: int = 300,
) -> CompressionResult:
    _validate_params(
        target_kb=target_kb,
        min_quality=min_quality,
        max_quality=max_quality,
        resize_step=resize_step,
        min_width=min_width,
        min_height=min_height,
    )

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"找不到输入文件: {input_path}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    target_bytes = target_kb * 1024

    with Image.open(input_file) as img:
        base_img = ImageOps.exif_transpose(img).convert("RGB")

    current_img = base_img
    best_candidate: Optional[_Candidate] = None
    steps: list[CompressionStep] = []
    round_index = 0

    while True:
        round_index += 1
        compressed_data, used_quality, used_size = _binary_search_jpeg_quality(
            current_img=current_img,
            target_bytes=target_bytes,
            min_quality=min_quality,
            max_quality=max_quality,
        )

        candidate = _Candidate(
            data=compressed_data,
            quality=used_quality,
            size_bytes=used_size,
            dimensions=current_img.size,
        )
        if _is_better_candidate(candidate, best_candidate, target_bytes):
            best_candidate = candidate

        steps.append(
            CompressionStep(
                round_index=round_index,
                quality=used_quality,
                size_bytes=used_size,
                dimensions=current_img.size,
            )
        )

        if used_size <= target_bytes:
            break

        width, height = current_img.size
        new_width = int(width * resize_step)
        new_height = int(height * resize_step)

        if new_width >= width and new_height >= height:
            break
        if new_width < min_width or new_height < min_height:
            break

        current_img = current_img.resize((new_width, new_height), Image.LANCZOS)

    if best_candidate is None:
        return CompressionResult(
            success=False,
            final_kb=0,
            quality=0,
            dimensions=(0, 0),
            output_path=str(output_file),
            final_bytes=0,
            reason="压缩失败：未得到有效输出。",
            steps=tuple(steps),
        )

    with open(output_file, "wb") as f:
        f.write(best_candidate.data)

    success = best_candidate.size_bytes <= target_bytes
    final_kb = math.ceil(best_candidate.size_bytes / 1024)
    reason = (
        "已达到目标大小。"
        if success
        else "未能达到目标大小：已到最小质量或最小分辨率限制。"
    )

    return CompressionResult(
        success=success,
        final_kb=final_kb,
        quality=best_candidate.quality,
        dimensions=best_candidate.dimensions,
        output_path=str(output_file),
        final_bytes=best_candidate.size_bytes,
        reason=reason,
        steps=tuple(steps),
    )

def _binary_search_jpeg_quality(
    current_img: Image.Image,
    target_bytes: int,
    min_quality: int,
    max_quality: int,
) -> Tuple[bytes, int, int]:
    best_under_data: Optional[bytes] = None
    best_under_quality = min_quality
    best_under_size = -1

    best_over_data: Optional[bytes] = None
    best_over_quality = min_quality
    best_over_size = math.inf

    low = min_quality
    high = max_quality

    while low <= high:
        mid = (low + high) // 2
        data = _save_jpeg_to_bytes(current_img, quality=mid)
        size = len(data)

        if size <= target_bytes:
            if size > best_under_size:
                best_under_data = data
                best_under_quality = mid
                best_under_size = size
            low = mid + 1
        else:
            if size < best_over_size:
                best_over_data = data
                best_over_quality = mid
                best_over_size = size
            high = mid - 1

    if best_under_data is not None:
        return best_under_data, best_under_quality, best_under_size

    if best_over_data is not None:
        return best_over_data, best_over_quality, best_over_size

    fallback_data = _save_jpeg_to_bytes(current_img, quality=min_quality)
    return fallback_data, min_quality, len(fallback_data)

def _save_jpeg_to_bytes(img: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    img.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buffer.getvalue()

