# codex_inet_gitpy_v2.ps1
# Codex をインターネット許可で起動し、Python(仮想環境)と Git の自動スナップショットを有効化するラッパー
# - サンドボックス無し（外部ネットワーク可）
# - 必要なら venv を自動作成し PATH に追加 → Codex から python が使える
# - 実行前/後に Git で自動コミット（差分がある時だけ）
# - PowerShell 5.1/7 互換

[CmdletBinding(PositionalBinding=$false)]
param(
    # 端末の文字化け対策
    [ValidateSet('utf8','cp932')]
    [string]$Encoding = 'cp932',

    # ===== Python (venv) 関連 =====
    [switch]$AutoVenv,                 # venv が無ければ自動作成
    [string]$VenvPath = '.\.venv',     # venv のパス（既定: .\.venv）
    [string]$PipRequirements,          # requirements.txt のパス（任意）

    # ===== Git 関連 =====
    [switch]$GitAuto = $true,          # pre/post 自動コミット
    [string]$GitUserName,              # 初回のみローカル設定したい場合
    [string]$GitUserEmail,             # 初回のみローカル設定したい場合
    [string]$GitRemote,                # origin を追加したい場合（任意）

    # ===== その他 =====
    [switch]$DryRun,                   # 実行せずコマンドだけ表示
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ForwardArgs             # Codex へ渡す引数
)

function Set-TerminalEncoding {
    param([string]$Mode)
    $cmdChcp = Get-Command chcp -ErrorAction SilentlyContinue
    if ($Mode -eq 'utf8') {
        $enc = [System.Text.UTF8Encoding]::new($false)
        if ($cmdChcp) { & $cmdChcp 65001 | Out-Null }
    } else {
        $enc = [System.Text.Encoding]::GetEncoding(932)
        if ($cmdChcp) { & $cmdChcp 932 | Out-Null }
    }
    $global:OutputEncoding = $enc
    [Console]::OutputEncoding = $enc
    [Console]::InputEncoding  = $enc
}

function Invoke-Step {
    param([string]$Cmd, [string]$What)
    if ($DryRun) {
        Write-Host "[DRYRUN] $What :: $Cmd"
        return $true
    } else {
        Write-Host ">> $What"
        & powershell -NoProfile -Command $Cmd
        return ($LASTEXITCODE -eq 0)
    }
}

Set-TerminalEncoding -Mode $Encoding

# ===== Codex 実行ファイル検出 =====
$codex = $null
$cmd = Get-Command codex -ErrorAction SilentlyContinue
if ($cmd) {
    if ($cmd.Path) { $codex = $cmd.Path }
    elseif ($cmd.Source) { $codex = $cmd.Source }
}
if (-not $codex -and $env:APPDATA) {
    $cand = Join-Path $env:APPDATA 'npm\codex.cmd'
    if (Test-Path -LiteralPath $cand) { $codex = $cand }
}
if (-not $codex) {
    $home = $HOME
    if (-not $home -and $env:USERPROFILE) { $home = $env:USERPROFILE }
    if ($home) {
        $cand2 = Join-Path $home 'AppData\Roaming\npm\codex.cmd'
        if (Test-Path -LiteralPath $cand2) { $codex = $cand2 }
    }
}
if (-not $codex) { $codex = 'codex' }

# ===== Python: venv 準備 =====
function Ensure-Venv {
    param([string]$PathVenv, [string]$ReqPath)
    $venvScripts = Join-Path $PathVenv 'Scripts'
    $pythonExe   = Join-Path $venvScripts 'python.exe'

    if ($AutoVenv) {
        if (-not (Test-Path -LiteralPath $venvScripts)) {
            $py = Get-Command py -ErrorAction SilentlyContinue
            $python = if ($py) { 'py -3' } else { 'python' }
            Invoke-Step -Cmd "$python -m venv `"$PathVenv`"" -What "Create venv: $PathVenv" | Out-Null
        }
    }

    if (Test-Path -LiteralPath $venvScripts) {
        # PATH 先頭に venv を追加（現在のプロセスのみ）
        $env:PATH = "$venvScripts;$env:PATH"
        # 必要なら requirements をインストール
        if ($ReqPath -and (Test-Path -LiteralPath $ReqPath)) {
            Invoke-Step -Cmd "`"$pythonExe`" -m pip install -U pip" -What "pip upgrade" | Out-Null
            Invoke-Step -Cmd "`"$pythonExe`" -m pip install -r `"$ReqPath`"" -What "pip install -r $ReqPath" | Out-Null
        }
    }
}
Ensure-Venv -PathVenv $VenvPath -ReqPath $PipRequirements

# ===== Git: 自動スナップショット =====
function Git-Available { return $null -ne (Get-Command git -ErrorAction SilentlyContinue) }
function Is-GitRepo { return (Test-Path -LiteralPath ".git") }
function Git-CommitIfChanged {
    param([string]$Msg)
    if (-not (Git-Available)) { return }
    $status = (& git status --porcelain)
    if ($status) {
        & git add -A
        & git commit -m $Msg | Out-Null
    }
}

if ($GitAuto -and (Git-Available)) {
    if (-not (Is-GitRepo)) {
        & git init | Out-Null
    }
    if ($GitUserName) { & git config user.name  $GitUserName }
    if ($GitUserEmail) { & git config user.email $GitUserEmail }

    # origin が未設定で -GitRemote が渡されたら追加
    if ($GitRemote) {
        $hasOrigin = (& git remote) -match '^origin$'
        if (-not $hasOrigin) { & git remote add origin $GitRemote }
    }

    Git-CommitIfChanged -Msg "pre-codex snapshot: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

# ===== Codex 実行（サンドボックス無し＝インターネット可） =====
$arguments = if ($ForwardArgs) { $ForwardArgs } else { @() }

if ($DryRun) {
    Write-Host "[DRYRUN] Launch Codex: $codex $($arguments -join ' ')"
    $code = 0
} else {
    & $codex @arguments
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 0 }
}

# ===== 実行後 Git スナップショット =====
if ($GitAuto -and (Git-Available)) {
    Git-CommitIfChanged -Msg "post-codex snapshot: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

exit $code
