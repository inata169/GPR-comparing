@echo off
setlocal

set "SCRIPT=%~dp0codex_safe_start_v2.ps1"
if not exist "%SCRIPT%" (
  echo [ERROR] codex_safe_start_v2.ps1 が見つかりません。(場所: %~dp0)
  exit /b 1
)

REM 既定では -Encoding cp932 で起動（必要に応じて引数で上書き可）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -Encoding cp932 %*
exit /b %ERRORLEVEL%
