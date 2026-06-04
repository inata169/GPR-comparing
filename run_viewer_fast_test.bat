@echo off
setlocal enabledelayedexpansion

echo ======================================================
echo rtgamma: Fast 3D Viewer PoC Test Batch
echo ======================================================

set PYTHONUTF8=1
set PYTHONPATH=%CD%

set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
    echo [INFO] Using venv Python: %PYTHON_EXE%
) else (
    echo [INFO] .venv not found. Using system Python.
    echo [INFO] To set up venv, run setup_fast_viewer_venv.bat
)

set CT_DIR=dicom\PROSTATE
set REF_FILE=dicom\PROSTATE\RTDOSE_2.16.840.1.114337.1.11224.1772428288.1.dcm
set EVAL_FILE=dicom\PROSTATE_MC\RTDOSE_2.16.840.1.114337.1.14324.1772511250.1.dcm
set GAMMA_NPZ=output\test_gamma_3d_mc.npz

if not exist "%CT_DIR%" (
    echo [ERROR] CT directory not found: %CT_DIR%
    pause
    exit /b 1
)
if not exist "%REF_FILE%" (
    echo [ERROR] Reference RTDOSE not found: %REF_FILE%
    pause
    exit /b 1
)
if not exist "%EVAL_FILE%" (
    echo [ERROR] Evaluation RTDOSE not found: %EVAL_FILE%
    pause
    exit /b 1
)

if not exist "%GAMMA_NPZ%" (
    echo [1/2] Computing 3D Gamma ^(MC vs Ref^)...
    if not exist "output" mkdir "output"
    "%PYTHON_EXE%" -m rtgamma.main ^
        --mode 3d ^
        --ref "%REF_FILE%" ^
        --eval "%EVAL_FILE%" ^
        --save-gamma-map "%GAMMA_NPZ%" ^
        --log-level INFO
    if errorlevel 1 (
        echo [ERROR] Gamma calculation failed.
        pause
        exit /b 1
    )
) else (
    echo [1/2] Using existing Gamma NPZ: %GAMMA_NPZ%
)

echo [2/2] Launching Fast 3D Viewer PoC...
"%PYTHON_EXE%" scripts\gamma_viewer_fast.py ^
    --ct "%CT_DIR%" ^
    --ref "%REF_FILE%" ^
    --eval "%EVAL_FILE%" ^
    --gamma-npz "%GAMMA_NPZ%"

if errorlevel 1 (
    echo [ERROR] Fast Viewer failed to launch.
    echo If dependencies are missing, run:
    echo   pip install -r requirements-fast-viewer.txt
    pause
    exit /b 1
)

echo Done.
pause
