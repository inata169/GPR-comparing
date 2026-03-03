@echo off
setlocal enabledelayedexpansion

echo ======================================================
echo rtgamma: 3D Viewer Test Batch (PROSTATE dataset MC vs Standard)
echo ======================================================

set PYTHONUTF8=1
set PYTHONPATH=%CD%

:: Define paths
set CT_DIR=dicom\PROSTATE
set REF_FILE=dicom\PROSTATE\RTDOSE_2.16.840.1.114337.1.11224.1772428288.1.dcm
set EVAL_FILE=dicom\PROSTATE_MC\RTDOSE_2.16.840.1.114337.1.14324.1772511250.1.dcm
set STRUCT_FILE=dicom\PROSTATE\RTSTRUCT_2.16.840.1.114337.1.11224.1772428287.0.dcm
set GAMMA_NPZ=output\test_gamma_3d_mc.npz

:: 1. Compute Gamma if NPZ doesn't exist
if not exist "%GAMMA_NPZ%" (
    echo [1/2] Computing 3D Gamma ^(MC vs Ref^)...
    if not exist "output" mkdir "output"
    python -m rtgamma.main ^
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

:: 2. Launch Viewer
echo [2/2] Launching 3D Viewer...
python scripts\gamma_viewer.py ^
    --ct "%CT_DIR%" ^
    --ref "%REF_FILE%" ^
    --eval "%EVAL_FILE%" ^
    --gamma-npz "%GAMMA_NPZ%" ^
    --rtstruct "%STRUCT_FILE%"

if errorlevel 1 (
    echo [ERROR] Viewer failed to launch.
    pause
    exit /b 1
)

echo Done.
pause
