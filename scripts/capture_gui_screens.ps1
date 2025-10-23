Param(
  [string]$OutDir = "docs/openspec/images",
  [int]$DelayMs = 1500
)

$ErrorActionPreference = 'Stop'

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32 {
  [DllImport("user32.dll", SetLastError=true, CharSet=CharSet.Auto)]
  public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
  [DllImport("user32.dll", SetLastError=true)]
  public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
}
public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
"@

Add-Type -AssemblyName System.Drawing

function Capture-WindowByTitle([string]$title, [string]$path){
  $h = [Win32]::FindWindow($null, $title)
  if ($h -eq [IntPtr]::Zero) { throw "Window not found: $title" }
  $rect = New-Object RECT
  if (-not [Win32]::GetWindowRect($h, [ref]$rect)) { throw "GetWindowRect failed" }
  $w = $rect.Right - $rect.Left
  $hgt = $rect.Bottom - $rect.Top
  if ($w -le 0 -or $hgt -le 0) { throw "Invalid window size" }
  $bmp = New-Object System.Drawing.Bitmap $w, $hgt
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
  $dir = Split-Path -Parent $path
  if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}

# Launch GUI
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'powershell'
$psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$($ROOT)\scripts\run_gui.ps1`""
$psi.WorkingDirectory = $ROOT
$psi.UseShellExecute = $true
$p = [System.Diagnostics.Process]::Start($psi)

Start-Sleep -Milliseconds $DelayMs

try {
  Capture-WindowByTitle -title 'rtgamma GUI Runner' -path (Join-Path $OutDir 'gui_main.png')
  Write-Host "Saved: $(Join-Path $OutDir 'gui_main.png')"
} catch {
  Write-Warning $_
}

Write-Host 'Optional: perform manual runs for 3D/2D, then re-run this script to capture additional states.'
Write-Host 'Examples:'
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\capture_gui_screens.ps1 -OutDir docs/openspec/images -DelayMs 1500"

