@echo off
setlocal EnableExtensions

set "BUNDLE_ROOT=%~dp0."
set "APP_DIR=%BUNDLE_ROOT%\app"
set "VENV_PYTHON=%APP_DIR%\.venv\Scripts\python.exe"
set "SMOKE_OUTPUT=%BUNDLE_ROOT%\smoke_output"

if not exist "%VENV_PYTHON%" (
    echo [ERROR] Dedicated environment is not installed.
    echo Run INSTALL_OFFLINE.bat first.
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONPATH=%APP_DIR%"
set "MPLBACKEND=Agg"
set "QT_QPA_PLATFORM=offscreen"
set "NUMBA_NUM_THREADS=1"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_CONFIG_FILE=NUL"

"%VENV_PYTHON%" "%APP_DIR%\offline\smoke_test.py" --output "%SMOKE_OUTPUT%"
exit /b %errorlevel%
