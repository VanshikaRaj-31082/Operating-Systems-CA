@echo off
setlocal
echo ========================================================
echo       LAUNCHING CA-6 MINI RUST OS IN QEMU
echo ========================================================
echo Workspace: %~dp0
cd /d "%~dp0"

if not exist "output\os.iso" (
    echo ERROR: output\os.iso not found!
    echo Please run scripts\build.sh first via WSL.
    pause
    exit /b 1
)

echo Checking QEMU availability...
where qemu-system-x86_64 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Starting QEMU directly on Windows...
    qemu-system-x86_64 -cdrom output\os.iso -serial stdio -vga std -m 256M
) else (
    echo Starting QEMU via WSL Ubuntu...
    wsl bash -c "qemu-system-x86_64 -cdrom output/os.iso -serial stdio -vga std -m 256M"
)

pause
