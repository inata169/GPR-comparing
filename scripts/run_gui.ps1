Param()

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Move to repo root and set PYTHONPATH
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $ROOT
$env:PYTHONPATH = $ROOT

# Load config (JSON)
$cfgPath = Join-Path $ROOT 'config/gui_defaults.json'
$cfg = @{}
if (Test-Path $cfgPath) {
  try { $cfg = Get-Content -Raw -Path $cfgPath | ConvertFrom-Json } catch { $cfg = @{} }
}

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
$form.Size = New-Object System.Drawing.Size(720,600)
$form.StartPosition = 'CenterScreen'
$form.Font = New-Object System.Drawing.Font('Segoe UI',9)
$form.BackColor = [System.Drawing.Color]::FromArgb(245,250,255)

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

# Plane index (auto or number)
$form.Controls.Add((New-Label 'Plane Index (auto or number)' 20 316))
$tbPlaneIndex = New-Object System.Windows.Forms.TextBox
$tbPlaneIndex.Location = New-Object System.Drawing.Point(20,340)
$tbPlaneIndex.Size = New-Object System.Drawing.Size(180,24)
$tbPlaneIndex.ReadOnly = $false
$tbPlaneIndex.Text = 'auto'
$form.Controls.Add($tbPlaneIndex)

# Optimize shift checkbox (default: off)
$cbOpt = New-Object System.Windows.Forms.CheckBox
$cbOpt.Text = 'Optimize shift'
$cbOpt.Location = New-Object System.Drawing.Point(320,260)
$cbOpt.AutoSize = $true
$cbOpt.Checked = $false
$form.Controls.Add($cbOpt)

# Local gamma checkbox (default: global)
$cbLocal = New-Object System.Windows.Forms.CheckBox
$cbLocal.Text = 'Local gamma'
$cbLocal.Location = New-Object System.Drawing.Point(320,288)
$cbLocal.AutoSize = $true
$cbLocal.Checked = $false
$form.Controls.Add($cbLocal)

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

# Options: open on finish, save log
$cbOpen = New-Object System.Windows.Forms.CheckBox
$cbOpen.Text = 'Open summary on finish'
$cbOpen.Location = New-Object System.Drawing.Point(340,288)
$cbOpen.AutoSize = $true
$cbOpen.Checked = $true
$form.Controls.Add($cbOpen)

$cbSaveLog = New-Object System.Windows.Forms.CheckBox
$cbSaveLog.Text = 'Save log to file'
$cbSaveLog.Location = New-Object System.Drawing.Point(520,288)
$cbSaveLog.AutoSize = $true
$cbSaveLog.Checked = $true
$form.Controls.Add($cbSaveLog)

# 3D NPZ save toggle
$cbSaveNPZ3D = New-Object System.Windows.Forms.CheckBox
$cbSaveNPZ3D.Text = 'Save 3D NPZ (gamma/diff)'
$cbSaveNPZ3D.Location = New-Object System.Drawing.Point(340,260)
$cbSaveNPZ3D.AutoSize = $true
$cbSaveNPZ3D.Checked = $false
$form.Controls.Add($cbSaveNPZ3D)

# Run / Open buttons
$btnRun = New-Button 'Run' 20 372 120 34
$btnCancel = New-Button 'Cancel' 160 372 120 34
$btnCancel.Enabled = $false
$btnOpen = New-Button 'Open Output' 300 372 160 34
$lblStatus = New-Label 'Status: Idle' 480 378
$pb = New-Object System.Windows.Forms.ProgressBar
$pb.Location = New-Object System.Drawing.Point(20, 412)
$pb.Size = New-Object System.Drawing.Size(660, 12)
$pb.Style = 'Marquee'
$pb.MarqueeAnimationSpeed = 25
$pb.Visible = $false
$form.Controls.Add($lblStatus)
$form.Controls.Add($btnRun)
$form.Controls.Add($btnCancel)
$form.Controls.Add($btnOpen)
$form.Controls.Add($pb)

# Log box
$tbLog = New-Object System.Windows.Forms.TextBox
$tbLog.Location = New-Object System.Drawing.Point(20,436)
$tbLog.Size = New-Object System.Drawing.Size(660,130)
$tbLog.Multiline = $true
$tbLog.ScrollBars = 'Vertical'
$tbLog.ReadOnly = $true
$form.Controls.Add($tbLog)

# Timer for elapsed time
$lblElapsed = New-Label 'Elapsed: 00:00' 480 354
$lblETA = New-Label 'ETA: --:--' 480 330
$form.Controls.Add($lblElapsed)
$form.Controls.Add($lblETA)
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 500
$script:startTime = $null
$script:proc = $null

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
      return @('python','-u','scripts/compare_rtdose_headers.py','--a',$ref,'--b',$eval,'--out',(Join-Path $out 'header_compare.md'))
    }
    1 { # 3D clinical
      $profile = Get-ProfileKey
      $optVal = 'off'
      if ($cbOpt.Checked) { $optVal = 'on' }
      $optArg = @('--opt-shift', $optVal)
      $gammaArg = @()
      if ($cbLocal.Checked) { $gammaArg = @('--gamma-type','local') }
      $baseCmd = @('python','-u','-m','rtgamma.main','--profile',$profile,'--ref',$ref,'--eval',$eval,'--mode','3d','--report',(Join-Path $out 'run3d')) + $optArg + $gammaArg + $threadsArg
      if ($cbSaveNPZ3D.Checked) {
        $baseCmd += @('--save-gamma-map',(Join-Path $out 'gamma3d.npz'),'--save-dose-diff',(Join-Path $out 'diff3d.npz'))
      }
      return $baseCmd
    }
    2 { # 2D clinical central slice
      $profile = Get-ProfileKey
      $plane = $cbPlane.SelectedItem
      $pindex = 'auto'
      if (-not [string]::IsNullOrWhiteSpace($tbPlaneIndex.Text)) {
        $pindex = $tbPlaneIndex.Text.Trim()
      }
      $optVal = 'off'
      if ($cbOpt.Checked) { $optVal = 'on' }
      $optArg = @('--opt-shift', $optVal)
      $gammaArg = @()
      if ($cbLocal.Checked) { $gammaArg = @('--gamma-type','local') }
      return @('python','-u','-m','rtgamma.main','--profile',$profile,'--ref',$ref,'--eval',$eval,'--mode','2d','--plane',$plane,'--plane-index',$pindex,'--save-gamma-map',(Join-Path $out ("${plane}_gamma.png")),'--save-dose-diff',(Join-Path $out ("${plane}_diff.png")),'--report',(Join-Path $out ("${plane}"))) + $optArg + $gammaArg + $threadsArg
    }
  }
}

function Run-Cmd([string[]]$cmd){
  Append-Log ("> " + ($cmd -join ' '))
  $btnRun.Enabled = $false; $btnRun.Text = 'Running...'; $btnCancel.Enabled = $true; $lblStatus.Text = 'Status: Running'; $pb.Visible = $true
  $script:startTime = Get-Date
  $timer.add_Tick({
    if ($script:startTime) {
      $elapsed = (Get-Date) - $script:startTime
      $mm = [int]$elapsed.TotalMinutes
      $ss = $elapsed.Seconds.ToString('00')
      $lblElapsed.Text = "Elapsed: $($mm):$($ss)"
      $lblETA.Text = 'ETA: --:--'
    }
  })
  $timer.Start()
  # Resolve python path for reliability
  $pyCmd = $cmd[0]
  if ($pyCmd -eq 'python') {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) {
      $py = (Get-Command py -ErrorAction SilentlyContinue).Source
      if ($py) { $pyCmd = $py; $cmd = @($pyCmd,'-3') + $cmd[1..($cmd.Length-1)] }
    } else { $pyCmd = $py }
  }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $pyCmd
  $psi.Arguments = ($cmd[1..($cmd.Length-1)] -join ' ')
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.WorkingDirectory = $ROOT
  $psi.EnvironmentVariables['PYTHONUNBUFFERED'] = '1'
  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  $p.EnableRaisingEvents = $true
  $script:proc = $p

  # Output event handlers
  # Marshal events to UI thread
  $p.SynchronizingObject = $form
  $null = $p.add_OutputDataReceived({ param($sender,$e) if ($e.Data) { $tbLog.AppendText($e.Data + "`r`n") } })
  $null = $p.add_ErrorDataReceived({ param($sender,$e) if ($e.Data) { $tbLog.AppendText($e.Data + "`r`n") } })
  $null = $p.add_Exited({ param($sender,$e)
      $code = $sender.ExitCode
      $btnRun.Enabled = $true; $btnRun.Text = 'Run'; $btnCancel.Enabled = $false; $lblStatus.Text = "Status: Done (Exit $code)"; $pb.Visible = $false; $timer.Stop(); $script:startTime = $null; $script:proc = $null
      if ($cbSaveLog.Checked -and -not [string]::IsNullOrWhiteSpace($tbOut.Text)) {
        try {
          $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
          $logPath = Join-Path $tbOut.Text ("run_log_" + $stamp + ".txt")
          $tbLog.Text | Out-File -FilePath $logPath -Encoding utf8
        } catch {}
      }
      if ($cbOpen.Checked -and -not [string]::IsNullOrWhiteSpace($tbOut.Text)) {
        try {
          # Prefer a summary PDF if present
          $pdf = Get-ChildItem -Path $tbOut.Text -Filter '*summary.pdf' -ErrorAction SilentlyContinue | Select-Object -First 1
          if ($pdf) { Start-Process $pdf.FullName }
          else {
            # Prefer an expected report name based on action
            $preferred = $null
            switch ($cbAction.SelectedIndex) {
              0 { $preferred = Join-Path $tbOut.Text 'header_compare.md' }
              1 { $preferred = Join-Path $tbOut.Text 'run3d.md' }
              2 { $preferred = Join-Path $tbOut.Text ("{0}.md" -f $cbPlane.SelectedItem) }
            }
            if ($preferred -and (Test-Path $preferred)) {
              Start-Process $preferred
            }
            else {
              # Fallback: open the most recently modified *.md under the folder
              $md = Get-ChildItem -Path $tbOut.Text -Filter '*.md' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
              if ($md) { Start-Process $md.FullName } else { Start-Process explorer.exe $tbOut.Text }
            }
          }
        } catch {}
      }
    })

  [void]$p.Start()
  $p.BeginOutputReadLine()
  $p.BeginErrorReadLine()
}

# Cancel support
$btnCancel.Add_Click({
  try {
    if ($script:proc -and -not $script:proc.HasExited) {
      $script:proc.Kill()
      $lblStatus.Text = 'Status: Canceled'
      $pb.Visible = $false
      $btnCancel.Enabled = $false
      $btnRun.Enabled = $true
      $btnRun.Text = 'Run'
      $timer.Stop(); $script:startTime = $null; $script:proc = $null
      Append-Log('Process canceled by user.')
    }
  } catch {}
})

# Apply config defaults to UI
try {
  if ($cfg.output_dir) { $tbOut.Text = [string]$cfg.output_dir }
  if ($cfg.plane_index) { $tbPlaneIndex.Text = [string]$cfg.plane_index } else { $tbPlaneIndex.Text = 'auto' }
  if ($cfg.save_npz_3d -ne $null) { $cbSaveNPZ3D.Checked = [bool]$cfg.save_npz_3d }
  if ($cfg.profile) {
    switch ([string]$cfg.profile) {
      'clinical_abs' { $cbProfile.SelectedIndex = 0 }
      'clinical_rel' { $cbProfile.SelectedIndex = 1 }
      'clinical_2x2' { $cbProfile.SelectedIndex = 2 }
      'clinical_3x3' { $cbProfile.SelectedIndex = 3 }
    }
  }
  if ($cfg.action) {
    switch ([string]$cfg.action) {
      'header' { $cbAction.SelectedIndex = 0 }
      '3d' { $cbAction.SelectedIndex = 1 }
      '2d' { $cbAction.SelectedIndex = 2 }
    }
  }
  if ($cfg.threads -ge 0) { $val = [int]$cfg.threads; if ($val -ge 0 -and $val -le $cpu) { $nudThreads.Value = [decimal]$val } }
  if ($cfg.open_on_finish -ne $null) { $cbOpen.Checked = [bool]$cfg.open_on_finish }
  if ($cfg.save_log -ne $null) { $cbSaveLog.Checked = [bool]$cfg.save_log }
} catch {}

# Save settings button
$btnSave = New-Button 'Save Settings' 540 330 140 34
$form.Controls.Add($btnSave)
$btnSave.Add_Click({
  $actionMap = @('header','3d','2d')
  $actionKey = $actionMap[[int]$cbAction.SelectedIndex]
  if (-not $actionKey) { $actionKey = '3d' }
  $new = [ordered]@{
    profile = (Get-ProfileKey)
    action = $actionKey
    threads = [int]$nudThreads.Value
    output_dir = $tbOut.Text
    open_on_finish = $cbOpen.Checked
    save_log = $cbSaveLog.Checked
    progress_marquee = $true
    plane_index = $tbPlaneIndex.Text
    save_npz_3d = $cbSaveNPZ3D.Checked
  }
  try { ($new | ConvertTo-Json -Depth 3) | Out-File -FilePath $cfgPath -Encoding utf8; [System.Windows.Forms.MessageBox]::Show('Saved.') } catch {}
})

$btnRun.Add_Click({
  $cmd = Build-Command
  if($null -ne $cmd){ Run-Cmd $cmd }
})

[void]$form.ShowDialog()
