@echo off
chcp 65001 >nul
REM ================================
REM Codex CLI 起動（承認なし）
REM sandbox: workspace-write
REM approvals: never
REM ================================

set "CODEX_PATH=%USERPROFILE%\AppData\Roaming\npm\codex.cmd"
if exist "%CODEX_PATH%" (set "CODEX=%CODEX_PATH%") else (set "CODEX=codex")

REM 必要に応じて作業フォルダへ移動
REM cd /d "C:\phits\work\Elekta\6MV\Rev70-c8-0.49n"

"%CODEX%" --sandbox workspace-write --ask-for-approval never %*
