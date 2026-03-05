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

# =============================================
#  Dark Theme Color Palette
# =============================================
$clrBg        = [System.Drawing.Color]::FromArgb(30, 30, 46)
$clrPanel     = [System.Drawing.Color]::FromArgb(40, 42, 60)
$clrInput     = [System.Drawing.Color]::FromArgb(55, 58, 80)
$clrAccent    = [System.Drawing.Color]::FromArgb(100, 149, 237)  # cornflower blue
$clrAccentH   = [System.Drawing.Color]::FromArgb(130, 170, 255)  # lighter hover
$clrGreen     = [System.Drawing.Color]::FromArgb(80, 200, 120)
$clrRed       = [System.Drawing.Color]::FromArgb(255, 100, 100)
$clrYellow    = [System.Drawing.Color]::FromArgb(255, 200, 60)
$clrText      = [System.Drawing.Color]::FromArgb(220, 225, 240)
$clrDimTxt    = [System.Drawing.Color]::FromArgb(140, 150, 170)
$clrSep       = [System.Drawing.Color]::FromArgb(60, 65, 90)

$fontMain     = New-Object System.Drawing.Font('Segoe UI', 9.5)
$fontTitle    = New-Object System.Drawing.Font('Segoe UI Semibold', 11)
$fontSect     = New-Object System.Drawing.Font('Segoe UI Semibold', 9.5)
$fontMono     = New-Object System.Drawing.Font('Consolas', 9)

# =============================================
#  Helper: Themed Controls
# =============================================
function New-DarkLabel($text, $x, $y, [System.Drawing.Font]$f = $fontMain, [System.Drawing.Color]$fg = $clrDimTxt){
  $lbl = New-Object System.Windows.Forms.Label
  $lbl.Text = $text; $lbl.Font = $f; $lbl.ForeColor = $fg
  $lbl.BackColor = [System.Drawing.Color]::Transparent
  $lbl.Location = New-Object System.Drawing.Point($x,$y); $lbl.AutoSize = $true
  return $lbl
}
function New-DarkTextBox($x, $y, $w=520, [bool]$ro=$true){
  $tb = New-Object System.Windows.Forms.TextBox
  $tb.Location = New-Object System.Drawing.Point($x,$y)
  $tb.Size = New-Object System.Drawing.Size($w,26)
  $tb.Font = $fontMain; $tb.ReadOnly = $ro
  $tb.BackColor = $clrInput; $tb.ForeColor = $clrText
  $tb.BorderStyle = 'FixedSingle'
  return $tb
}
function New-DarkButton($text, $x, $y, $w=90, $h=30){
  $btn = New-Object System.Windows.Forms.Button
  $btn.Text = $text; $btn.Font = $fontMain
  $btn.Location = New-Object System.Drawing.Point($x,$y)
  $btn.Size = New-Object System.Drawing.Size($w,$h)
  $btn.FlatStyle = 'Flat'
  $btn.FlatAppearance.BorderColor = $clrAccent
  $btn.FlatAppearance.BorderSize = 1
  $btn.BackColor = $clrPanel; $btn.ForeColor = $clrAccent
  $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
  $btn.Add_MouseEnter({ $this.BackColor = $clrAccent; $this.ForeColor = $clrBg })
  $btn.Add_MouseLeave({ $this.BackColor = $clrPanel; $this.ForeColor = $clrAccent })
  return $btn
}
function New-DarkCheck($text, $x, $y, [bool]$checked=$false){
  $cb = New-Object System.Windows.Forms.CheckBox
  $cb.Text = $text; $cb.Font = $fontMain
  $cb.Location = New-Object System.Drawing.Point($x,$y)
  $cb.AutoSize = $true; $cb.Checked = $checked
  $cb.ForeColor = $clrText; $cb.BackColor = [System.Drawing.Color]::Transparent
  return $cb
}
function New-DarkCombo($x, $y, $w=220, $items){
  $cb = New-Object System.Windows.Forms.ComboBox
  $cb.Location = New-Object System.Drawing.Point($x,$y)
  $cb.Size = New-Object System.Drawing.Size($w,26)
  $cb.DropDownStyle = 'DropDownList'
  $cb.Font = $fontMain; $cb.BackColor = $clrInput; $cb.ForeColor = $clrText
  $cb.FlatStyle = 'Flat'
  $cb.Items.AddRange($items)
  return $cb
}
function New-Separator($y, $w=720){
  $p = New-Object System.Windows.Forms.Panel
  $p.Location = New-Object System.Drawing.Point(20, $y)
  $p.Size = New-Object System.Drawing.Size($w, 1)
  $p.BackColor = $clrSep
  return $p
}

# =============================================
#  Form
# =============================================
$form = New-Object System.Windows.Forms.Form
$form.Text = 'rtgamma  |  Gamma Analysis Tool'
# Adapt height to screen: use 90% of screen height if screen is small
$screenH = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea.Height
$formH = [Math]::Min(1010, [int]($screenH * 0.92))
$form.Size = New-Object System.Drawing.Size(780, $formH)
$form.StartPosition = 'CenterScreen'
$form.Font = $fontMain
$form.BackColor = $clrBg
$form.ForeColor = $clrText
$form.FormBorderStyle = 'Sizable'
$form.MaximizeBox = $true
$form.AutoScroll = $true
$form.MinimumSize = New-Object System.Drawing.Size(600, 400)

# Title banner
$lblTitle = New-DarkLabel 'rtgamma  -  DICOM RTDOSE Gamma Analysis' 24 14 $fontTitle $clrAccent
$form.Controls.Add($lblTitle)
$lblSubTitle = New-DarkLabel 'Configure parameters and run 2D / 3D gamma pass-rate evaluation' 24 38 $fontMain $clrDimTxt
$form.Controls.Add($lblSubTitle)
$form.Controls.Add((New-Separator 62 720))

# =============================================
#  Section: File Paths
# =============================================
$yf = 72
$form.Controls.Add((New-DarkLabel 'FILE PATHS' 24 $yf $fontSect $clrAccent))
$yf += 24

# Ref
$form.Controls.Add((New-DarkLabel 'Reference RTDOSE' 24 $yf))
$yf += 20
$tbRef = New-DarkTextBox 24 $yf 600
$btnRef = New-DarkButton 'Browse' 640 $yf
$form.Controls.Add($tbRef); $form.Controls.Add($btnRef)
$yf += 34

# Eval
$form.Controls.Add((New-DarkLabel 'Evaluation RTDOSE' 24 $yf))
$yf += 20
$tbEval = New-DarkTextBox 24 $yf 600
$btnEval = New-DarkButton 'Browse' 640 $yf
$form.Controls.Add($tbEval); $form.Controls.Add($btnEval)
$yf += 34

# RTSTRUCT
$form.Controls.Add((New-DarkLabel 'RTSTRUCT  (optional)' 24 $yf))
$yf += 20
$tbStruct = New-DarkTextBox 24 $yf 600
$btnStruct = New-DarkButton 'Browse' 640 $yf
$form.Controls.Add($tbStruct); $form.Controls.Add($btnStruct)
$yf += 34

# ROI
$form.Controls.Add((New-DarkLabel 'ROI Names  (comma separated, e.g. PTV,GTV - blank = all)' 24 $yf))
$yf += 20
$tbRoi = New-DarkTextBox 24 $yf 600 $false
$form.Controls.Add($tbRoi)
$yf += 34

# Output
$form.Controls.Add((New-DarkLabel 'Output Folder' 24 $yf))
$yf += 20
$tbOut = New-DarkTextBox 24 $yf 600
$btnOut = New-DarkButton 'Select' 640 $yf
$form.Controls.Add($tbOut); $form.Controls.Add($btnOut)
$yf += 34

# CT Directory (for 3D Viewer)
$form.Controls.Add((New-DarkLabel 'CT Directory  (for 3D Viewer)' 24 $yf))
$yf += 20
$tbCT = New-DarkTextBox 24 $yf 600
$btnCT = New-DarkButton 'Select' 640 $yf
$form.Controls.Add($tbCT); $form.Controls.Add($btnCT)
$yf += 38

$form.Controls.Add((New-Separator ($yf) 720))
$yf += 10

# =============================================
#  Section: Gamma Parameters  (DTA / DD / Cutoff)
# =============================================
$form.Controls.Add((New-DarkLabel 'GAMMA PARAMETERS' 24 $yf $fontSect $clrAccent))
$yf += 28

# Preset Profile
$presetsPath = Join-Path $ROOT 'config/presets.json'
$script:presets = @{}
if (Test-Path $presetsPath) {
  try { $script:presets = Get-Content -Raw -Path $presetsPath -Encoding UTF8 | ConvertFrom-Json } catch { $script:presets = @{} }
}
$form.Controls.Add((New-DarkLabel 'Preset' 24 $yf))
$cbPreset = New-DarkCombo 90 ($yf - 2) 150 @('Custom')
if ($script:presets.PSObject.Properties.Name.Count -gt 0) {
  foreach ($p in $script:presets.PSObject.Properties) {
    $null = $cbPreset.Items.Add($p.Name)
  }
}
$cbPreset.SelectedIndex = 0
$form.Controls.Add($cbPreset)

$yf += 36

# DTA
$form.Controls.Add((New-DarkLabel 'DTA  [mm]' 24 $yf))
$tbDTA = New-DarkTextBox 130 ($yf - 2) 80 $false
$tbDTA.Text = '2.0'; $tbDTA.TextAlign = 'Center'
$form.Controls.Add($tbDTA)

# DD
$form.Controls.Add((New-DarkLabel 'DD  [%]' 250 $yf))
$tbDD = New-DarkTextBox 340 ($yf - 2) 80 $false
$tbDD.Text = '3.0'; $tbDD.TextAlign = 'Center'
$form.Controls.Add($tbDD)

# Cutoff
$form.Controls.Add((New-DarkLabel 'Cutoff  [%]' 460 $yf))
$tbCutoff = New-DarkTextBox 570 ($yf - 2) 80 $false
$tbCutoff.Text = '10.0'; $tbCutoff.TextAlign = 'Center'
$form.Controls.Add($tbCutoff)

$yf += 36
$form.Controls.Add((New-Separator ($yf) 720))
$yf += 10

# =============================================
#  Section: Analysis Settings
# =============================================
$form.Controls.Add((New-DarkLabel 'ANALYSIS SETTINGS' 24 $yf $fontSect $clrAccent))
$yf += 28

# Action
$form.Controls.Add((New-DarkLabel 'Action' 24 $yf))
$cbAction = New-DarkCombo 130 ($yf - 2) 180 @('Header Compare','3D Gamma','2D Gamma','3D Viewer')
$cbAction.SelectedIndex = 1
$form.Controls.Add($cbAction)

# Norm
$form.Controls.Add((New-DarkLabel 'Norm' 340 $yf))
$cbNorm = New-DarkCombo 410 ($yf - 2) 180 @('global_max','max_ref','none')
$cbNorm.SelectedIndex = 0
$form.Controls.Add($cbNorm)

# Event to populate parameters when preset changes (requires cbNorm to be initialized)
$cbPreset.add_SelectedIndexChanged({
  $sel = $cbPreset.SelectedItem
  if ($sel -ne 'Custom' -and $script:presets.$sel) {
    if ($script:presets.$sel.dta -ne $null) { $tbDTA.Text = [string]$script:presets.$sel.dta }
    if ($script:presets.$sel.dd -ne $null) { $tbDD.Text = [string]$script:presets.$sel.dd }
    if ($script:presets.$sel.cutoff -ne $null) { $tbCutoff.Text = [string]$script:presets.$sel.cutoff }
    if ($script:presets.$sel.norm) {
      $idx = $cbNorm.Items.IndexOf([string]$script:presets.$sel.norm)
      if ($idx -ge 0) { $cbNorm.SelectedIndex = $idx }
    }
  }
})

$yf += 36

# 2D Plane
$form.Controls.Add((New-DarkLabel '2D Plane' 24 $yf))
$cbPlane = New-DarkCombo 130 ($yf - 2) 120 @('axial','sagittal','coronal')
$cbPlane.SelectedIndex = 0
$form.Controls.Add($cbPlane)

# Plane Index
$form.Controls.Add((New-DarkLabel 'Plane Index' 270 $yf))
$tbPlaneIdx = New-DarkTextBox 370 ($yf - 2) 80 $false
$tbPlaneIdx.Text = 'auto'; $tbPlaneIdx.TextAlign = 'Center'
$form.Controls.Add($tbPlaneIdx)

# Threads
$cpu = [Environment]::ProcessorCount
$form.Controls.Add((New-DarkLabel "Threads (max=$cpu)" 480 $yf))
$nudThreads = New-Object System.Windows.Forms.NumericUpDown
$nudThreads.Location = New-Object System.Drawing.Point(620, ($yf - 2))
$nudThreads.Size = New-Object System.Drawing.Size(80, 26)
$nudThreads.Font = $fontMain; $nudThreads.BackColor = $clrInput; $nudThreads.ForeColor = $clrText
$nudThreads.Minimum = 0; $nudThreads.Maximum = [decimal]$cpu; $nudThreads.Value = [decimal]$cpu
$nudThreads.BorderStyle = 'FixedSingle'
$form.Controls.Add($nudThreads)

$yf += 38

# Checkboxes row
$cbOpt    = New-DarkCheck 'Optimize Shift' 24 $yf $false
$cbLocal  = New-DarkCheck 'Local Gamma' 160 $yf $false
$cbNPZ    = New-DarkCheck 'Save 3D NPZ' 290 $yf $false
$cbDB     = New-DarkCheck 'Save to DB' 420 $yf $true
$cbLog    = New-DarkCheck 'Save Log' 540 $yf $true
$form.Controls.Add($cbOpt); $form.Controls.Add($cbLocal); $form.Controls.Add($cbNPZ); $form.Controls.Add($cbDB); $form.Controls.Add($cbLog)

$yf += 28
$cbOpen   = New-DarkCheck 'Open summary on finish' 24 $yf $true
$form.Controls.Add($cbOpen)

$form.Controls.Add((New-DarkLabel 'Sub-voxel Interp' 290 $yf))
$nudInterp = New-Object System.Windows.Forms.NumericUpDown
$nudInterp.Location = New-Object System.Drawing.Point(420, ($yf - 2))
$nudInterp.Size = New-Object System.Drawing.Size(60, 26)
$nudInterp.Font = $fontMain; $nudInterp.BackColor = $clrInput; $nudInterp.ForeColor = $clrText
$nudInterp.Minimum = 1; $nudInterp.Maximum = 20; $nudInterp.Value = 10
$nudInterp.BorderStyle = 'FixedSingle'
$form.Controls.Add($nudInterp)
$yf += 34

$form.Controls.Add((New-Separator ($yf) 720))
$yf += 10

# =============================================
#  Section: Run Controls
# =============================================
$form.Controls.Add((New-DarkLabel 'RUN' 24 $yf $fontSect $clrAccent))
$yf += 28

# Run button (prominent green)
$btnRun = New-Object System.Windows.Forms.Button
$btnRun.Text = '>> Run'; $btnRun.Font = New-Object System.Drawing.Font('Segoe UI Semibold',11)
$btnRun.Location = New-Object System.Drawing.Point(24, $yf)
$btnRun.Size = New-Object System.Drawing.Size(140, 40)
$btnRun.FlatStyle = 'Flat'; $btnRun.FlatAppearance.BorderSize = 0
$btnRun.BackColor = $clrGreen; $btnRun.ForeColor = $clrBg
$btnRun.Cursor = [System.Windows.Forms.Cursors]::Hand
$btnRun.Add_MouseEnter({ $this.BackColor = [System.Drawing.Color]::FromArgb(100, 230, 140) })
$btnRun.Add_MouseLeave({ $this.BackColor = $clrGreen })
$form.Controls.Add($btnRun)

# Cancel
$btnCancel = New-DarkButton 'Cancel' 180 $yf 100 40
$btnCancel.Enabled = $false
$btnCancel.FlatAppearance.BorderColor = $clrRed; $btnCancel.ForeColor = $clrRed
$btnCancel.Add_MouseEnter({ $this.BackColor = $clrRed; $this.ForeColor = $clrBg })
$btnCancel.Add_MouseLeave({ $this.BackColor = $clrPanel; $this.ForeColor = $clrRed })
$form.Controls.Add($btnCancel)

# Open Output
$btnOpen = New-DarkButton 'Open Output' 300 $yf 130 40
$form.Controls.Add($btnOpen)

# Save Settings
$btnSave = New-DarkButton 'Save Settings' 570 $yf 140 40
$form.Controls.Add($btnSave)

$yf += 48

# Status / Elapsed
$lblStatus  = New-DarkLabel 'Status: Idle' 24 $yf $fontMain $clrDimTxt
$lblElapsed = New-DarkLabel 'Elapsed: --:--' 480 $yf $fontMain $clrDimTxt
$form.Controls.Add($lblStatus); $form.Controls.Add($lblElapsed)
$yf += 22

# Progress bar
$pb = New-Object System.Windows.Forms.ProgressBar
$pb.Location = New-Object System.Drawing.Point(24, $yf)
$pb.Size = New-Object System.Drawing.Size(710, 6)
$pb.Style = 'Marquee'; $pb.MarqueeAnimationSpeed = 20; $pb.Visible = $false
$form.Controls.Add($pb)
$yf += 14

# Log output
$tbLog = New-Object System.Windows.Forms.TextBox
$tbLog.Location = New-Object System.Drawing.Point(24, $yf)
$tbLog.Size = New-Object System.Drawing.Size(710, 280)
$tbLog.Multiline = $true; $tbLog.ScrollBars = 'Vertical'; $tbLog.ReadOnly = $true
$tbLog.Font = $fontMono; $tbLog.BackColor = [System.Drawing.Color]::FromArgb(22, 22, 34); $tbLog.ForeColor = $clrGreen
$tbLog.BorderStyle = 'FixedSingle'
$form.Controls.Add($tbLog)

# =============================================
#  Timer
# =============================================
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 500
$script:startTime = $null
$script:proc = $null

# =============================================
#  Events
# =============================================
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
$btnStruct.Add_Click({ Browse-File ([ref]$tbStruct) })
$btnCT.Add_Click({ Browse-Folder ([ref]$tbCT) })
$btnOut.Add_Click({ Browse-Folder ([ref]$tbOut) })
$btnOpen.Add_Click({ if(-not [string]::IsNullOrWhiteSpace($tbOut.Text)) { Start-Process explorer.exe $tbOut.Text } })

# =============================================
#  Build Command
# =============================================
function Build-Command(){
  $ref = $tbRef.Text; $eval = $tbEval.Text; $out = $tbOut.Text
  if([string]::IsNullOrWhiteSpace($ref) -or [string]::IsNullOrWhiteSpace($eval) -or [string]::IsNullOrWhiteSpace($out)){
    [System.Windows.Forms.MessageBox]::Show('Please select Ref / Eval / Output folder.','Missing Input','OK','Warning')
    return $null
  }
  New-Item -ItemType Directory -Force -Path $out | Out-Null

  # Validate numeric inputs
  $dd = 0.0; $dta = 0.0; $cutoff = 0.0
  if (-not [double]::TryParse($tbDD.Text, [ref]$dd) -or $dd -le 0) {
    [System.Windows.Forms.MessageBox]::Show('DD must be a positive number.','Invalid Input','OK','Warning'); return $null
  }
  if (-not [double]::TryParse($tbDTA.Text, [ref]$dta) -or $dta -le 0) {
    [System.Windows.Forms.MessageBox]::Show('DTA must be a positive number.','Invalid Input','OK','Warning'); return $null
  }
  if (-not [double]::TryParse($tbCutoff.Text, [ref]$cutoff) -or $cutoff -lt 0) {
    [System.Windows.Forms.MessageBox]::Show('Cutoff must be a non-negative number.','Invalid Input','OK','Warning'); return $null
  }

  $threadsArg = @()
  if([int]$nudThreads.Value -gt 0){ $threadsArg = @('--threads', [int]$nudThreads.Value) }

  $normVal = $cbNorm.SelectedItem
  if ([string]::IsNullOrWhiteSpace($normVal)) { $normVal = 'global_max' }

  # Common gamma args
  $interpVal = [int]$nudInterp.Value
  $gammaArgs = @('--dd', $dd, '--dta', $dta, '--cutoff', $cutoff, '--norm', $normVal, '--interp-fraction', $interpVal)
  if ($cbPreset.SelectedItem -ne 'Custom') { $gammaArgs += @('--profile', $cbPreset.SelectedItem) }
  if ($cbLocal.Checked) { $gammaArgs += @('--gamma-type','local') }
  if ($cbDB.Checked) { $gammaArgs += @('--db', (Join-Path $out 'rtgamma.db')) }
  if (-not [string]::IsNullOrWhiteSpace($tbStruct.Text)) { $gammaArgs += @('--rtstruct', $tbStruct.Text.Trim()) }
  if (-not [string]::IsNullOrWhiteSpace($tbRoi.Text)) {
    foreach ($r in $tbRoi.Text.Split(',')) { if(-not [string]::IsNullOrWhiteSpace($r)) { $gammaArgs += @('--roi', $r.Trim()) } }
  }

  $optVal = if ($cbOpt.Checked) { 'on' } else { 'off' }
  $optArg = @('--opt-shift', $optVal)

  switch ($cbAction.SelectedIndex){
    0 { # Header compare
      return @('python','-u','scripts/compare_rtdose_headers.py','--a',$ref,'--b',$eval,'--out',(Join-Path $out 'header_compare.md'))
    }
    1 { # 3D
      $baseCmd = @('python','-u','-m','rtgamma.main','--ref',$ref,'--eval',$eval,'--mode','3d','--report',(Join-Path $out 'run3d')) + $optArg + $gammaArgs + $threadsArg
      if ($cbNPZ.Checked) {
        $baseCmd += @('--save-gamma-map',(Join-Path $out 'gamma3d.npz'),'--save-dose-diff',(Join-Path $out 'diff3d.npz'))
      }
      return $baseCmd
    }
    2 { # 2D
      $plane = $cbPlane.SelectedItem
      $pindex = 'auto'
      if (-not [string]::IsNullOrWhiteSpace($tbPlaneIdx.Text)) { $pindex = $tbPlaneIdx.Text.Trim() }
      return @('python','-u','-m','rtgamma.main','--ref',$ref,'--eval',$eval,'--mode','2d','--plane',$plane,'--plane-index',$pindex,
        '--save-gamma-map',(Join-Path $out ("${plane}_gamma.png")),
        '--save-dose-diff',(Join-Path $out ("${plane}_diff.png")),
        '--report',(Join-Path $out $plane)) + $optArg + $gammaArgs + $threadsArg
    }
    3 { # 3D Viewer
      $ct = $tbCT.Text
      if([string]::IsNullOrWhiteSpace($ct)){
        [System.Windows.Forms.MessageBox]::Show('Please select CT Directory for the 3D Viewer.','Missing Input','OK','Warning')
        return $null
      }
      $viewerCmd = @('python','-u','scripts/gamma_viewer.py','--ct',$ct,'--ref',$ref,'--eval',$eval,
        '--dd',$dd,'--dta',$dta,'--cutoff',$cutoff)
      if (-not [string]::IsNullOrWhiteSpace($tbStruct.Text)) { $viewerCmd += @('--rtstruct', $tbStruct.Text.Trim()) }
      if (-not [string]::IsNullOrWhiteSpace($tbRoi.Text)) {
        $viewerCmd += @('--roi', $tbRoi.Text.Trim())
      }
      # If a pre-computed NPZ exists in output folder, use it
      $npzPath = Join-Path $out 'gamma3d.npz'
      if (Test-Path $npzPath) {
        $viewerCmd += @('--gamma-npz', $npzPath)
      }
      return $viewerCmd
    }
  }
}

# =============================================
#  Run process
# =============================================
function Run-Cmd([string[]]$cmd){
  Append-Log ("> " + ($cmd -join ' '))
  $btnRun.Enabled = $false; $btnRun.Text = 'Running...'; $btnCancel.Enabled = $true
  $lblStatus.Text = 'Status: Running'; $lblStatus.ForeColor = $clrYellow
  $pb.Visible = $true
  $script:startTime = Get-Date
  $timer.add_Tick({
    if ($script:startTime) {
      $elapsed = (Get-Date) - $script:startTime
      $mm = [int]$elapsed.TotalMinutes; $ss = $elapsed.Seconds.ToString('00')
      $lblElapsed.Text = "Elapsed: $($mm):$($ss)"
    }
  })
  $timer.Start()

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
  $psi.EnvironmentVariables['PYTHONUTF8'] = '1'
  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  $p.EnableRaisingEvents = $true
  $script:proc = $p
  $p.SynchronizingObject = $form

  $null = $p.add_OutputDataReceived({ param($sender,$e) if ($e.Data) { $tbLog.AppendText($e.Data + "`r`n") } })
  $null = $p.add_ErrorDataReceived({ param($sender,$e) if ($e.Data) { $tbLog.AppendText($e.Data + "`r`n") } })
  $null = $p.add_Exited({ param($sender,$e)
      $code = $sender.ExitCode
      $btnRun.Enabled = $true; $btnRun.Text = '>> Run'; $btnCancel.Enabled = $false
      $pb.Visible = $false; $timer.Stop(); $script:startTime = $null; $script:proc = $null
      if ($code -eq 0) {
        $lblStatus.Text = "Status: Done (Exit 0)"; $lblStatus.ForeColor = $clrGreen
      } else {
        $lblStatus.Text = "Status: Error (Exit $code)"; $lblStatus.ForeColor = $clrRed
      }
      if ($cbLog.Checked -and -not [string]::IsNullOrWhiteSpace($tbOut.Text)) {
        try {
          $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
          $logPath = Join-Path $tbOut.Text ("run_log_" + $stamp + ".txt")
          $tbLog.Text | Out-File -FilePath $logPath -Encoding utf8
        } catch {}
      }
      if ($cbOpen.Checked -and -not [string]::IsNullOrWhiteSpace($tbOut.Text)) {
        try {
          $pdf = Get-ChildItem -Path $tbOut.Text -Filter '*summary.pdf' -ErrorAction SilentlyContinue | Select-Object -First 1
          if ($pdf) { Start-Process $pdf.FullName }
          else {
            $preferred = $null
            switch ($cbAction.SelectedIndex) {
              0 { $preferred = Join-Path $tbOut.Text 'header_compare.md' }
              1 { $preferred = Join-Path $tbOut.Text 'run3d.md' }
              2 { $preferred = Join-Path $tbOut.Text ("{0}.md" -f $cbPlane.SelectedItem) }
            }
            if ($preferred -and (Test-Path $preferred)) { Start-Process $preferred }
            else {
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

# =============================================
#  Run process for Viewer (needs visible window for matplotlib)
# =============================================
function Run-Viewer([string[]]$cmd){
  Append-Log ("> " + ($cmd -join ' '))
  $lblStatus.Text = 'Status: Launching Viewer...'; $lblStatus.ForeColor = $clrYellow

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
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $false
  $psi.RedirectStandardOutput = $false
  $psi.RedirectStandardError = $false
  $psi.WorkingDirectory = $ROOT
  $psi.EnvironmentVariables['PYTHONUNBUFFERED'] = '1'
  $psi.EnvironmentVariables['PYTHONUTF8'] = '1'

  try {
    $p = [System.Diagnostics.Process]::Start($psi)
    $lblStatus.Text = 'Status: Viewer launched'; $lblStatus.ForeColor = $clrGreen
    Append-Log('Viewer process started (PID=' + $p.Id + '). Window should appear shortly.')
  } catch {
    $lblStatus.Text = 'Status: Error launching viewer'; $lblStatus.ForeColor = $clrRed
    Append-Log('ERROR: ' + $_.Exception.Message)
  }
}

# Cancel
$btnCancel.Add_Click({
  try {
    if ($script:proc -and -not $script:proc.HasExited) {
      $script:proc.Kill()
      $lblStatus.Text = 'Status: Canceled'; $lblStatus.ForeColor = $clrRed
      $pb.Visible = $false; $btnCancel.Enabled = $false
      $btnRun.Enabled = $true; $btnRun.Text = '>> Run'
      $timer.Stop(); $script:startTime = $null; $script:proc = $null
      Append-Log('Process canceled by user.')
    }
  } catch {}
})

# =============================================
#  Apply saved config defaults
# =============================================
try {
  if ($cfg.output_dir)  { $tbOut.Text = [string]$cfg.output_dir }
  if ($cfg.ct_dir)      { $tbCT.Text = [string]$cfg.ct_dir }
  if ($cfg.plane_index) { $tbPlaneIdx.Text = [string]$cfg.plane_index } else { $tbPlaneIdx.Text = 'auto' }
  if ($cfg.save_npz_3d -ne $null)    { $cbNPZ.Checked = [bool]$cfg.save_npz_3d }
  if ($cfg.save_db -ne $null)        { $cbDB.Checked = [bool]$cfg.save_db }
  if ($cfg.rtstruct -ne $null)       { $tbStruct.Text = [string]$cfg.rtstruct }
  if ($cfg.roi -ne $null)            { $tbRoi.Text = [string]$cfg.roi }
  if ($cfg.open_on_finish -ne $null) { $cbOpen.Checked = [bool]$cfg.open_on_finish }
  if ($cfg.save_log -ne $null)       { $cbLog.Checked = [bool]$cfg.save_log }
  if ($cfg.threads -ge 0) { $val = [int]$cfg.threads; if ($val -ge 0 -and $val -le $cpu) { $nudThreads.Value = [decimal]$val } }
  if ($cfg.interp_fraction -ge 1) { $val = [int]$cfg.interp_fraction; if ($val -ge 1 -and $val -le 20) { $nudInterp.Value = [decimal]$val } }
  if ($cfg.action) {
    switch ([string]$cfg.action) {
      'header' { $cbAction.SelectedIndex = 0 }
      '3d'     { $cbAction.SelectedIndex = 1 }
      '2d'     { $cbAction.SelectedIndex = 2 }
      'viewer' { $cbAction.SelectedIndex = 3 }
    }
  }
  # Load gamma params from config
  if ($cfg.dd)     { $tbDD.Text     = [string]$cfg.dd }
  if ($cfg.dta)    { $tbDTA.Text    = [string]$cfg.dta }
  if ($cfg.cutoff) { $tbCutoff.Text = [string]$cfg.cutoff }
  if ($cfg.norm)   {
    $normIdx = $cbNorm.Items.IndexOf([string]$cfg.norm)
    if ($normIdx -ge 0) { $cbNorm.SelectedIndex = $normIdx }
  }
  if ($cfg.profile) {
    $profIdx = $cbPreset.Items.IndexOf([string]$cfg.profile)
    if ($profIdx -ge 0) { $cbPreset.SelectedIndex = $profIdx }
  }
} catch {}

# Save settings
$btnSave.Add_Click({
  $actionMap = @('header','3d','2d','viewer')
  $actionKey = $actionMap[[int]$cbAction.SelectedIndex]
  if (-not $actionKey) { $actionKey = '3d' }
  $new = [ordered]@{
    dd          = $tbDD.Text
    dta         = $tbDTA.Text
    cutoff      = $tbCutoff.Text
    norm        = $cbNorm.SelectedItem
    action      = $actionKey
    threads     = [int]$nudThreads.Value
    output_dir  = $tbOut.Text
    ct_dir      = $tbCT.Text
    open_on_finish = $cbOpen.Checked
    save_log    = $cbLog.Checked
    save_db     = $cbDB.Checked
    plane_index = $tbPlaneIdx.Text
    save_npz_3d = $cbNPZ.Checked
    rtstruct    = $tbStruct.Text
    roi         = $tbRoi.Text
    interp_fraction = [int]$nudInterp.Value
    profile     = $cbPreset.SelectedItem
  }
  try { ($new | ConvertTo-Json -Depth 3) | Out-File -FilePath $cfgPath -Encoding utf8; [System.Windows.Forms.MessageBox]::Show('Settings saved.','rtgamma','OK','Information') } catch {}
})

$btnRun.Add_Click({
  $cmd = Build-Command
  if($null -ne $cmd){
    if ($cbAction.SelectedIndex -eq 3) {
      Run-Viewer $cmd
    } else {
      Run-Cmd $cmd
    }
  }
})

[void]$form.ShowDialog()
