#!/usr/bin/env bash
set -euo pipefail

ENTRY="${1:-main.py}"
NAME="${2:-image-compressor}"
VERSION="${3:-1.0.0}"

if [[ ! -f "$ENTRY" ]]; then
  echo "Entry script not found: $ENTRY" >&2
  exit 1
fi

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Linux) PLATFORM="linux" ;;
  Darwin) PLATFORM="macos" ;;
  *)
    echo "Unsupported OS: $OS" >&2
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64|amd64) ARCH_TAG="x64" ;;
  arm64|aarch64) ARCH_TAG="arm64" ;;
  *)
    ARCH_TAG="$ARCH"
    ;;
esac

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "Building ${NAME} ..."
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --onefile --name "$NAME" "$ENTRY"

OUT_DIR="dist"
RAW_BIN="${OUT_DIR}/${NAME}"
FINAL_BASE="${NAME}-v${VERSION}-${PLATFORM}-${ARCH_TAG}"
FINAL_BIN="${OUT_DIR}/${FINAL_BASE}"
ARCHIVE="${OUT_DIR}/${FINAL_BASE}.tar.gz"
SUM_FILE="${OUT_DIR}/SHA256SUMS.txt"

if [[ ! -f "$RAW_BIN" ]]; then
  echo "Build output not found: $RAW_BIN" >&2
  exit 1
fi

mv -f "$RAW_BIN" "$FINAL_BIN"
chmod +x "$FINAL_BIN"
tar -czf "$ARCHIVE" -C "$OUT_DIR" "$(basename "$FINAL_BIN")"

hash_cmd="sha256sum"
if ! command -v sha256sum >/dev/null 2>&1; then
  hash_cmd="shasum -a 256"
fi

{
  $hash_cmd "$FINAL_BIN" | awk '{print $1 "  '"$(basename "$FINAL_BIN")"'"}'
  $hash_cmd "$ARCHIVE" | awk '{print $1 "  '"$(basename "$ARCHIVE")"'"}'
} > "$SUM_FILE"

echo "Done."
echo "Binary : $FINAL_BIN"
echo "Archive: $ARCHIVE"
echo "Checks : $SUM_FILE"
