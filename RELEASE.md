# Image Compressor Release Guide

> 使用与功能说明请先阅读 [README.md](./README.md)

## 1. Purpose
This project packages `main.py` into standalone binaries so users can run it without installing Python.

## 2. Dependencies (build machine only)
```bash
python -m pip install -r requirements.txt
```

## 3. Local Build

### Windows (PowerShell)
```powershell
.\package.ps1
# or
.\build.ps1 -Version 1.0.0
```

### macOS / Linux
```bash
chmod +x build.sh
./build.sh main.py image-compressor 1.0.0
```

Build outputs are placed in `dist/`:
- Executable: `image-compressor-v{version}-{platform}-{arch}` (`.exe` on Windows)
- Archive: `.zip` (Windows) or `.tar.gz` (macOS/Linux)
- Checksums: `SHA256SUMS.txt`

## 4. User Usage (No Python Needed)
After unzip/untar, users can run:

### CLI mode
```bash
image-compressor img/input/input.png -k 200
image-compressor img/input/input.png -k 200 -o out.jpg
image-compressor img/input/input.png -k 200 --overwrite --verbose
```

### Interactive mode
Run executable without parameters, then use menu options.

By default:
- Input assets are organized under `img/input/`
- Generated outputs are written to `img/output/` (unless `-o` is provided)

## 5. Drag-and-Drop (Windows)
Users can drag an image file onto `image-compressor-v1.0.0-windows-x64.exe`.
The executable will receive the file path as the first positional argument.

## 6. Common Issues
- `Permission denied` on macOS/Linux: run `chmod +x <binary>` first.
- `Output file exists`: use `--overwrite` or pass another `-o` path.
- `No such file`: check path quoting for spaces/non-ASCII chars.
- SmartScreen / Gatekeeper warning: unsigned binaries may require manual allow.

## 7. SHA256 Verification
Compare downloaded file hash with `SHA256SUMS.txt`.

### Windows
```powershell
Get-FileHash .\image-compressor-v1.0.0-windows-x64.exe -Algorithm SHA256
```

### macOS / Linux
```bash
sha256sum image-compressor-v1.0.0-linux-x64
# or
shasum -a 256 image-compressor-v1.0.0-macos-x64
```

The hash must exactly match the corresponding line in `SHA256SUMS.txt`.
