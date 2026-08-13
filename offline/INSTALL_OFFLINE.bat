@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "BUNDLE_ROOT=%~dp0."
set "APP_DIR=%BUNDLE_ROOT%\app"
set "PYTHON_DIR=%BUNDLE_ROOT%\runtime\python312"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "SELECTED_PYTHON_FILE=%BUNDLE_ROOT%\runtime\selected-python.txt"
set "VENV_DIR=%APP_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PY_INSTALLER=%BUNDLE_ROOT%\python\python-3.12.10-amd64.exe"
set "PYTHON_INSTALL_LOG=%BUNDLE_ROOT%\python_install.log"

set "PYTHONUTF8=1"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_CONFIG_FILE=NUL"

echo ============================================================
echo GPR-comparing offline installer - Python 3.12 x64
echo ============================================================
echo.

echo [1/7] Verifying bundle SHA-256 checksums...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BUNDLE_ROOT%\VERIFY_BUNDLE.ps1" -BundleRoot "%BUNDLE_ROOT%"
if errorlevel 1 goto :fail

if not exist "%PYTHON_EXE%" (
    echo [2/7] Checking for an existing external Python 3.12...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BUNDLE_ROOT%\CHECK_EXISTING_PYTHON.ps1" -BundledPythonDir "%PYTHON_DIR%" -SelectedPythonPathFile "%SELECTED_PYTHON_FILE%" -VenvDir "%VENV_DIR%"
    set "PREFLIGHT_RC=!ERRORLEVEL!"
    if not "!PREFLIGHT_RC!"=="0" (
        if "!PREFLIGHT_RC!"=="12" echo [ERROR] Safety preflight stopped installation before the Python installer was launched.
        if not "!PREFLIGHT_RC!"=="12" echo [ERROR] Python safety preflight failed with exit code !PREFLIGHT_RC!.
        goto :fail
    )

    if exist "%SELECTED_PYTHON_FILE%" (
        if not exist "%VENV_PYTHON%" (
            echo [ERROR] External Python did not create the dedicated virtual environment.
            goto :fail
        )
        set "PYTHON_EXE=%VENV_PYTHON%"
        echo [3/7] Using compatible external Python only to create the dedicated virtual environment.
    ) else (
        echo [3/7] Installing bundled Python 3.12.10 locally...
        if not exist "%PY_INSTALLER%" (
            echo [ERROR] Python installer is missing: %PY_INSTALLER%
            goto :fail
        )
        if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"
        start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_launcher=0 InstallLauncherAllUsers=0 PrependPath=0 Include_test=0 Shortcuts=0 /log "%PYTHON_INSTALL_LOG%"
        if errorlevel 1 (
            echo [ERROR] Python installer failed. See: %PYTHON_INSTALL_LOG%
            goto :fail
        )
        if not exist "%PYTHON_EXE%" (
            echo [ERROR] Python installer did not create: %PYTHON_EXE%
            echo See installer log: %PYTHON_INSTALL_LOG%
            goto :fail
        )
    )
) else (
    echo [2/7] Bundled runtime detected; external Python check is not needed.
    echo [3/7] Bundled Python is already installed.
)

"%PYTHON_EXE%" -I -c "import struct,sys; assert sys.implementation.name == 'cpython', sys.implementation.name; assert sys.version_info[:2] == (3,12), sys.version; assert struct.calcsize('P') == 8, '64-bit Python required'"
if errorlevel 1 goto :fail

if not exist "%VENV_PYTHON%" (
    echo [4/7] Creating dedicated virtual environment...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
) else (
    echo [4/7] Dedicated virtual environment already exists.
)

echo [5/7] Installing only from the local wheelhouse...
"%VENV_PYTHON%" -m pip install --no-index --find-links "%BUNDLE_ROOT%\wheelhouse" -r "%APP_DIR%\offline\requirements-offline.txt"
if errorlevel 1 goto :fail

echo [6/7] Checking Python 3.12 and runtime imports...
"%VENV_PYTHON%" -c "import struct,sys; assert sys.version_info[:2] == (3,12), sys.version; assert struct.calcsize('P') == 8; import pydicom,numpy,scipy,numba,matplotlib,reportlab,PySide6,pyqtgraph; print(sys.version); print('Runtime imports: OK')"
if errorlevel 1 goto :fail

echo [7/7] Running non-patient DICOM smoke test...
call "%BUNDLE_ROOT%\RUN_SMOKE_TEST.bat"
if errorlevel 1 goto :fail

echo.
echo [SUCCESS] GPR-comparing was installed and verified.
echo Launch with: LAUNCH_GPR_COMPARING.bat
if not defined GPR_OFFLINE_NO_PAUSE pause
exit /b 0

:fail
echo.
echo [ERROR] Installation failed. Review the messages above.
echo No internet source was used by pip.
if not defined GPR_OFFLINE_NO_PAUSE pause
exit /b 1
