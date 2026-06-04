@echo off
setlocal

REM rtgamma GUI launcher for source/Python mode.
REM This does not use the packaged EXE launcher.
set SCRIPT_DIR=%~dp0
set PYTHONUTF8=1
set PYTHONPATH=%SCRIPT_DIR%

echo Launching rtgamma GUI (Python/source mode)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\run_gui.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to launch Python/source mode GUI.
    pause
    exit /b 1
)
