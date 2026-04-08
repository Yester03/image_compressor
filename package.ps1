param(
    [string]$Entry = "main.py",
    [string]$Name = "image-compressor",
    [string]$Version = "1.0.0",
    [string]$VenvDir = ".venv-min"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Entry)) {
    throw "未找到入口脚本: $Entry"
}

if (-not (Test-Path -LiteralPath $VenvDir)) {
    Write-Host "Creating minimal build venv: $VenvDir"
    python -m venv $VenvDir
}

$venvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "未找到虚拟环境 Python: $venvPython"
}

Write-Host "Using venv python: $venvPython"
& $venvPython -m pip install --disable-pip-version-check --upgrade pip
& $venvPython -m pip install --disable-pip-version-check pillow pyinstaller

& ".\build.ps1" -Entry $Entry -Name $Name -Version $Version -PythonExe $venvPython
