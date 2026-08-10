@echo off
setlocal EnableExtensions

set "BUNDLE_ROOT=%~dp0."
set "APP_DIR=%BUNDLE_ROOT%\app"
set "VENV_PYTHON=%APP_DIR%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Dedicated environment is not installed.
    echo Run INSTALL_OFFLINE.bat first.
    pause
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONPATH=%APP_DIR%"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_CONFIG_FILE=NUL"

call "%APP_DIR%\run_gui_python.bat"
exit /b %errorlevel%
