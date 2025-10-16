Param()

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Move to repo root and set PYTHONPATH
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT
$env:PYTHONPATH = $ROOT

function New-Label($text, $x, $y){
  $lbl = New-Object System.Windows.Forms.Label
  $lbl.Text = $text
  $lbl.Location = New-Object System.Drawing.Point($x,$y)
  $lbl.AutoSize = $true
  return $lbl
}
function New-Button($text, $x, $y, $w=80, $h=28){
  $btn = New-Object System.Windows.Forms.Button
  $btn.Text = $text
  $btn.Location = New-Object System.Drawing.Point($x,$y)
  $btn.Size = New-Object System.Drawing.Size($w,$h)
  return $btn
}
function New-TextBox($x, $y, $w=420){
  $tb = New-Object System.Windows.Forms.TextBox
  $tb.Location = New-Object System.Drawing.Point($x,$y)
  $tb.Size = New-Object System.Drawing.Size($w,24)
  $tb.ReadOnly = $true
  return $tb
}

# Form
$form = New-Object System.Windows.Forms.Form
$form.Text = 'rtgamma GUI Runner'
$form.Size = New-Object System.Drawing.Size(720,560)
$form.StartPosition = 'CenterScreen'

# REF / EVAL selectors
$form.Controls.Add((New-Label 'Ref RTDOSE (.dcm)' 20 20))
$tbRef = New-TextBox 20 44 560
$btnRef = New-Button 'Browse...' 600 42
$form.Controls.Add($tbRef)
$form.Controls.Add($btnRef)

$form.Controls.Add((New-Label 'Eval RTDOSE (.dcm)' 20 80))
$tbEval = New-TextBox 20 104 560
$btnEval = New-Button 'Browse...' 600 102
$form.Controls.Add($tbEval)
$form.Controls.Add($btnEval)

# Output folder
$form.Controls.Add((New-Label 'Output Folder' 20 140))
$tbOut = New-TextBox 20 164 560
$btnOut = New-Button 'Select...' 600 162
$form.Controls.Add($tbOut)
$form.Controls.Add($btnOut)

# Action
$form.Controls.Add((New-Label 'Action' 20 204))
$cbAction = New-Object System.Windows.Forms.ComboBox
$cbAction.Location = New-Object System.Drawing.Point(20,228)
$cbAction.Size = New-Object System.Drawing.Size(260,24)
$cbAction.DropDownStyle = 'DropDownList'
$cbAction.Items.AddRange(@('Header Compare','3D (clinical preset)','2D (clinical preset)'))
$cbAction.SelectedIndex = 1
$form.Controls.Add($cbAction)

# Preset profile
$form.Controls.Add((New-Label 'Clinical Preset' 320 204))
$cbProfile = New-Object System.Windows.Forms.ComboBox
$cbProfile.Location = New-Object System.Drawing.Point(320,228)
$cbProfile.Size = New-Object System.Drawing.Size(260,24)
$cbProfile.DropDownStyle = 'DropDownList'
$cbProfile.Items.AddRange(@('clinical_abs (abs 3%/2mm/10%)','clinical_rel (rel 3%/2mm/10%)','clinical_2x2 (2%/2mm/10%)','clinical_3x3 (3%/3mm/10%)'))
$cbProfile.SelectedIndex = 1
$form.Controls.Add($cbProfile)

# 2D plane
$form.Controls.Add((New-Label '2D Plane' 20 264))
$cbPlane = New-Object System.Windows.Forms.ComboBox
$cbPlane.Location = New-Object System.Drawing.Point(20,288)
$cbPlane.Size = New-Object System.Drawing.Size(180,24)
$cbPlane.DropDownStyle = 'DropDownList'
$cbPlane.Items.AddRange(@('axial','sagittal','coronal'))
$cbPlane.SelectedIndex = 0
$form.Controls.Add($cbPlane)

# Threads
$cpu = [Environment]::ProcessorCount
$form.Controls.Add((New-Label "Threads (optional, 0=auto, max=$cpu)" 220 264))
$nudThreads = New-Object System.Windows.Forms.NumericUpDown
$nudThreads.Location = New-Object System.Drawing.Point(220,288)
$nudThreads.Size = New-Object System.Drawing.Size(100,24)
$nudThreads.Minimum = 0
$nudThreads.Maximum = [decimal]$cpu
$nudThreads.Value = [decimal]$cpu
$form.Controls.Add($nudThreads)

# Run / Open buttons
$btnRun = New-Button 'Run' 20 330 120 34
$btnOpen = New-Button 'Open Output' 160 330 160 34
$lblStatus = New-Label 'Status: Idle' 340 336
$form.Controls.Add($lblStatus)
$form.Controls.Add($btnRun)
$form.Controls.Add($btnOpen)

# Log box
$tbLog = New-Object System.Windows.Forms.TextBox
$tbLog.Location = New-Object System.Drawing.Point(20,380)
$tbLog.Size = New-Object System.Drawing.Size(660,130)
$tbLog.Multiline = $true
$tbLog.ScrollBars = 'Vertical'
$tbLog.ReadOnly = $true
$form.Controls.Add($tbLog)

function Append-Log($text){ $tbLog.AppendText("$text`r`n") }

function Browse-File([ref]$tb){
  $dlg = New-Object System.Windows.Forms.OpenFileDialog
  $dlg.Filter = 'DICOM (*.dcm)|*.dcm|All files (*.*)|*.*'
  if($dlg.ShowDialog() -eq 'OK'){ $tb.Value.Text = $dlg.FileName }
}
function Browse-Folder([ref]$tb){
  $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
  if($dlg.ShowDialog() -eq 'OK'){ $tb.Value.Text = $dlg.SelectedPath }
}

$btnRef.Add_Click({ Browse-File ([ref]$tbRef) })
$btnEval.Add_Click({ Browse-File ([ref]$tbEval) })
$btnOut.Add_Click({ Browse-Folder ([ref]$tbOut) })
$btnOpen.Add_Click({ if([string]::IsNullOrWhiteSpace($tbOut.Text)) { return } else { Start-Process explorer.exe $tbOut.Text } })

function Get-ProfileKey(){
  switch ($cbProfile.SelectedIndex){
    0 { 'clinical_abs' }
    1 { 'clinical_rel' }
    2 { 'clinical_2x2' }
    3 { 'clinical_3x3' }
    default { 'clinical_rel' }
  }
}

function Build-Command(){
  $ref = $tbRef.Text; $eval = $tbEval.Text; $out = $tbOut.Text
  if([string]::IsNullOrWhiteSpace($ref) -or [string]::IsNullOrWhiteSpace($eval) -or [string]::IsNullOrWhiteSpace($out)){
    [System.Windows.Forms.MessageBox]::Show('Please select Ref/Eval/Output folder.'); return $null
  }
  New-Item -ItemType Directory -Force -Path $out | Out-Null

  $threadsArg = @()
  if([int]$nudThreads.Value -gt 0){ $threadsArg = @('--threads', [int]$nudThreads.Value) }

  switch ($cbAction.SelectedIndex){
    0 { # Header compare
      return @('python','scripts/compare_rtdose_headers.py','--a',$ref,'--b',$eval,'--out',(Join-Path $out 'header_compare.md'))
    }
    1 { # 3D clinical
      $profile = Get-ProfileKey
      return @('python','-m','rtgamma.main','--profile',$profile,'--ref',$ref,'--eval',$eval,'--mode','3d','--report',(Join-Path $out 'run3d')) + $threadsArg
    }
    2 { # 2D clinical central slice
      $profile = Get-ProfileKey
      $plane = $cbPlane.SelectedItem
      return @('python','-m','rtgamma.main','--profile',$profile,'--ref',$ref,'--eval',$eval,'--mode','2d','--plane',$plane,'--plane-index','auto','--save-gamma-map',(Join-Path $out "${plane}_gamma.png"),'--save-dose-diff',(Join-Path $out "${plane}_diff.png"),'--report',(Join-Path $out "${plane}")) + $threadsArg
    }
  }
}

function Run-Cmd([string[]]$cmd){
  Append-Log ("> " + ($cmd -join ' '))
  $btnRun.Enabled = $false; $btnRun.Text = 'Running...'; $lblStatus.Text = 'Status: Running'
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $cmd[0]
  $psi.Arguments = ($cmd[1..($cmd.Length-1)] -join ' ')
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  $p.EnableRaisingEvents = $true

  # Output event handlers
  Register-ObjectEvent -InputObject $p -EventName OutputDataReceived -Action {
    if($Event.SourceEventArgs.Data){
      $null = $form.BeginInvoke([Action]{ $tbLog.AppendText($Event.SourceEventArgs.Data + "`r`n") })
    }
  } | Out-Null
  Register-ObjectEvent -InputObject $p -EventName ErrorDataReceived -Action {
    if($Event.SourceEventArgs.Data){
      $null = $form.BeginInvoke([Action]{ $tbLog.AppendText($Event.SourceEventArgs.Data + "`r`n") })
    }
  } | Out-Null
  Register-ObjectEvent -InputObject $p -EventName Exited -Action {
    $code = $Event.Sender.ExitCode
    $null = $form.BeginInvoke([Action]{
      $btnRun.Enabled = $true; $btnRun.Text = 'Run'; $lblStatus.Text = "Status: Done (Exit $code)"
    })
  } | Out-Null

  [void]$p.Start()
  $p.BeginOutputReadLine()
  $p.BeginErrorReadLine()
}

$btnRun.Add_Click({
  $cmd = Build-Command
  if($null -ne $cmd){ Run-Cmd $cmd }
})

[void]$form.ShowDialog()
