# codex_safe_start_v6.ps1
# - chcp が無い環境でもエラーにしない
# - 文字化け対策（utf8/cp932 切替）
# - 引数はそのまま Codex にパススルー
# - PowerShell 5.1 / 7 で動作

[CmdletBinding(PositionalBinding=$false)]
param(
    [ValidateSet('utf8','cp932')]
    [string]$Encoding = 'cp932',

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ForwardArgs
)

function Set-TerminalEncoding {
    param([string]$Mode)

    # chcp の有無を判定（無ければ呼ばない）
    $hasChcp = $false
    $cmdChcp = Get-Command chcp -ErrorAction SilentlyContinue
    if ($cmdChcp) { $hasChcp = $true }

    if ($Mode -eq 'utf8') {
        $enc = [System.Text.UTF8Encoding]::new($false)
        if ($hasChcp) { & $cmdChcp 65001 | Out-Null }
    } else {
        $enc = [System.Text.Encoding]::GetEncoding(932)
        if ($hasChcp) { & $cmdChcp 932 | Out-Null }
    }

    $global:OutputEncoding = $enc
    [Console]::OutputEncoding = $enc
    [Console]::InputEncoding  = $enc
}

Set-TerminalEncoding -Mode $Encoding

# ===== Codex 実行ファイルの検出 =====
$codex = $null

# 1) PATH 上
$cmd = Get-Command codex -ErrorAction SilentlyContinue
if ($cmd) {
    if ($cmd.Path) { $codex = $cmd.Path }
    elseif ($cmd.Source) { $codex = $cmd.Source }
}

# 2) APPDATA\npm\codex.cmd
if (-not $codex -and $env:APPDATA) {
    $cand = Join-Path $env:APPDATA 'npm\codex.cmd'
    if (Test-Path -LiteralPath $cand) { $codex = $cand }
}

# 3) HOME/USERPROFILE 既知パス
if (-not $codex) {
    $home = $HOME
    if (-not $home -and $env:USERPROFILE) { $home = $env:USERPROFILE }
    if ($home) {
        $cand2 = Join-Path $home 'AppData\Roaming\npm\codex.cmd'
        if (Test-Path -LiteralPath $cand2) { $codex = $cand2 }
    }
}

# 4) 最後に名前だけ（PATH 解決に委ねる）
if (-not $codex) { $codex = 'codex' }

# ===== 引数組み立て =====
$baseArgs = @('--sandbox','workspace-write','--ask-for-approval','never')
if ($ForwardArgs) {
    $arguments = $baseArgs + $ForwardArgs
} else {
    $arguments = $baseArgs
}

# ===== 実行 =====
& $codex @arguments
$code = $LASTEXITCODE
if ($null -eq $code) { $code = 0 }
exit $code
