# codex_min.ps1
# 最小構成版: エンコードやコードページを変更せず、Codexだけを実行します。

# Codex 実行ファイル(.cmd)の既定インストール場所を探す。なければ 'codex' を直接呼ぶ。
$codexPath = Join-Path $env:USERPROFILE 'AppData\Roaming\npm\codex.cmd'
if (Test-Path $codexPath) {
    $codex = $codexPath
} else {
    $codex = 'codex'
}

# 安全フラグを付与し、渡された引数をそのまま連結
$forwardArgs = @('--sandbox','workspace-write','--ask-for-approval','never') + $args

& $codex @forwardArgs
exit $LASTEXITCODE
