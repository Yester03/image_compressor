param(
    [string]$Entry = "main.py",
    [string]$Name = "image-compressor",
    [string]$Version = "1.0.0",
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Entry)) {
    throw "Entry script not found: $Entry"
}

$platform = "windows"
$arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
$exeName = "$Name.exe"
$finalBaseName = "$Name-v$Version-$platform-$arch"
$finalName = "$finalBaseName.exe"
$zipName = "$finalBaseName.zip"

Write-Host "Building $exeName ..."
& $PythonExe -m PyInstaller --noconfirm --clean --onefile --name $Name $Entry
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 执行失败，退出码: $LASTEXITCODE"
}

$exePath = Join-Path "dist" $exeName
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Build output not found: $exePath"
}

$finalExePath = Join-Path "dist" $finalName
Move-Item -LiteralPath $exePath -Destination $finalExePath -Force

$zipPath = Join-Path "dist" $zipName
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path $finalExePath -DestinationPath $zipPath -Force

$hashExe = (Get-FileHash -LiteralPath $finalExePath -Algorithm SHA256).Hash.ToLower()
$hashZip = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower()
$sumFile = Join-Path "dist" "SHA256SUMS.txt"

@(
    "$hashExe  $finalName"
    "$hashZip  $zipName"
) | Set-Content -LiteralPath $sumFile -Encoding UTF8

Write-Host "Done."
Write-Host "Binary : $finalExePath"
Write-Host "Archive: $zipPath"
Write-Host "Checks : $sumFile"
