@echo off
setlocal

echo ======================================================
echo rtgamma: Fast Viewer venv setup
echo ======================================================

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/3] Creating virtual environment: %VENV_DIR%
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Using existing virtual environment: %VENV_DIR%
)

echo [2/3] Upgrading pip...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo [3/3] Installing dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r REQUIREMENTS.txt -r requirements-fast-viewer.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Setup complete.
echo Next: double-click run_viewer_fast_test.bat
pause
