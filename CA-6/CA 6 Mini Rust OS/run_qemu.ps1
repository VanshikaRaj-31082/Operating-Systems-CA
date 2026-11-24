# CA-6 Mini Rust OS: PowerShell QEMU Launcher
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      LAUNCHING CA-6 MINI RUST OS IN QEMU" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

if (-not (Test-Path "output\os.iso")) {
    Write-Host "ERROR: output\os.iso not found! Please build first." -ForegroundColor Red
    exit 1
}

$qemuWindows = Get-Command "qemu-system-x86_64" -ErrorAction SilentlyContinue

if ($qemuWindows) {
    Write-Host "Found QEMU in Windows PATH. Booting ISO..." -ForegroundColor Green
    & qemu-system-x86_64 -cdrom output\os.iso -serial stdio -vga std -m 256M
} else {
    Write-Host "Launching QEMU through WSL Ubuntu..." -ForegroundColor Green
    wsl bash -c "qemu-system-x86_64 -cdrom output/os.iso -serial stdio -vga std -m 256M"
}
