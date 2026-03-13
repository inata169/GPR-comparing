@echo off
set SCRIPT_DIR=%~dp0
echo Launching rtgamma GUI (Portable Mode via EXE-based PowerShell script)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\run_gui_exe.ps1"
pause
