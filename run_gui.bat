@echo off
REM Simple launcher for the rtgamma GUI (no keyboard required)
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\run_gui.ps1"

