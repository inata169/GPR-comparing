function Read-GuiIni([string]$path) {
  $result = [ordered]@{}
  $section = '_root'
  if (-not (Test-Path $path)) { return $result }
  foreach ($line in (Get-Content -Path $path -Encoding UTF8)) {
    $l = $line.Trim()
    if ($l -eq '' -or $l.StartsWith('#') -or $l.StartsWith(';')) { continue }
    if ($l -match '^\[(.+)\]$') {
      $section = $Matches[1].Trim()
      if (-not $result.Contains($section)) { $result[$section] = [ordered]@{} }
    } elseif ($l -match '^([^=]+)=(.*)$') {
      $key = $Matches[1].Trim()
      $val = $Matches[2].Trim()
      if (-not $result.Contains($section)) { $result[$section] = [ordered]@{} }
      $result[$section][$key] = $val
    }
  }
  return $result
}

function Write-GuiIni([string]$path, [System.Collections.Specialized.OrderedDictionary]$data) {
  $lines = @()
  foreach ($sec in $data.Keys) {
    $lines += "[$sec]"
    foreach ($k in $data[$sec].Keys) {
      $lines += "$k = $($data[$sec][$k])"
    }
    $lines += ''
  }
  $lines | Out-File -FilePath $path -Encoding utf8
}

function Flatten-GuiIni([System.Collections.Specialized.OrderedDictionary]$ini) {
  $cfg = @{}
  foreach ($sec in $ini.Keys) {
    foreach ($k in $ini[$sec].Keys) { $cfg[$k] = $ini[$sec][$k] }
  }
  return $cfg
}

function Read-GuiDefaults([string]$root) {
  $cfg = @{}
  $jsonPath = Join-Path $root 'config/gui_defaults.json'
  if (Test-Path $jsonPath) {
    try {
      $jsonObj = Get-Content -Raw -Path $jsonPath -Encoding UTF8 | ConvertFrom-Json
      foreach ($p in $jsonObj.PSObject.Properties) { $cfg[$p.Name] = $p.Value }
    } catch {}
  }
  return $cfg
}

function Read-GuiConfig([string]$root) {
  $iniPath = Join-Path $root 'config/gui_config.ini'
  if (Test-Path -LiteralPath $iniPath -PathType Leaf) {
    return Flatten-GuiIni (Read-GuiIni $iniPath)
  }
  $examplePath = Join-Path $root 'config/gui_config.example.ini'
  return Flatten-GuiIni (Read-GuiIni $examplePath)
}

function Merge-GuiConfig([hashtable]$defaults, [hashtable]$saved) {
  $merged = @{}
  foreach ($k in $defaults.Keys) { $merged[$k] = $defaults[$k] }
  foreach ($k in $saved.Keys) { $merged[$k] = $saved[$k] }
  return $merged
}

function Resolve-ViewerType([hashtable]$config, [string]$fallback = 'fast') {
  $normalizedFallback = ([string]$fallback).ToLowerInvariant()
  if ($normalizedFallback -ne 'legacy' -and $normalizedFallback -ne 'fast') {
    $normalizedFallback = 'fast'
  }

  $raw = $null
  if ($config.ContainsKey('viewer_type')) {
    $raw = [string]$config['viewer_type']
  }
  $normalized = ''
  if ($null -ne $raw) {
    $normalized = $raw.Trim().ToLowerInvariant()
  }
  if ($normalized -eq 'legacy' -or $normalized -eq 'fast') {
    return [pscustomobject]@{
      Value = $normalized
      IsFallback = $false
      RawValue = $raw
      Message = $null
    }
  }

  $reason = if ([string]::IsNullOrWhiteSpace($raw)) { 'missing' } else { "invalid: $raw" }
  return [pscustomobject]@{
    Value = $normalizedFallback
    IsFallback = $true
    RawValue = $raw
    Message = "viewer_type is $reason; using $normalizedFallback for this launch. Save Settings to write a normalized value."
  }
}
