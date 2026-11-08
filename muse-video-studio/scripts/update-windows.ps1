param([string]$Target)
$ErrorActionPreference = 'Stop'
try {
  $payload = Join-Path $PSScriptRoot 'app'
  $manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'UPDATE-MANIFEST.json') -Raw | ConvertFrom-Json
  if (-not $Target) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $picker.Description = 'Chon thu muc BAN CU co tep Muse AI Studio.exe (khong chon resources/app)'
    if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $Target = $picker.SelectedPath
  }
  $Target = [IO.Path]::GetFullPath($Target)
  $executable = Join-Path $Target 'Muse AI Studio.exe'
  $appPath = Join-Path $Target 'resources\app'
  if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw 'Thu muc chon khong co Muse AI Studio.exe. Hay chon dung thu muc ban cu.' }
  $old = Get-Content -LiteralPath (Join-Path $appPath 'package.json') -Raw | ConvertFrom-Json
  if ($old.name -ne 'muse-ai-studio' -or $old.version -notin @('1.8.0','1.9.0')) { throw 'Goi cap nhat nay danh cho ban Windows 1.8.0 / 1.9.0. Ban khac can goi day du.' }
  $running = @(Get-Process -Name 'Muse AI Studio' -ErrorAction SilentlyContinue | Where-Object { try { $_.Path -eq $executable } catch { $false } })
  if ($running.Count) { throw 'Hay dong toan bo cua so Muse AI Studio ban cu roi chay cap nhat lai. Khong tu dong tat cac tac vu dang tao.' }
  $records = @()
  foreach ($property in $manifest.appFiles.PSObject.Properties) {
    $relative = $property.Name
    if ($relative -match '(^|[\\/])\.\.([\\/]|$)|^[/\\]|:|(^|[\\/])\.data([\\/]|$)|(^|[\\/])\.env($|[\\/])' -or $relative -notmatch '^(desktop/|dist/|[A-Za-z0-9_.-]+$)') { throw 'Duong dan trong goi cap nhat khong hop le.' }
    $source = Join-Path $payload $relative
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { throw 'Goi cap nhat sai SHA256. Tai va giai nen lai goi cap nhat.' }
    $records += [PSCustomObject]@{ Relative=$relative; Source=$source; Destination=(Join-Path $appPath $relative); Existed=(Test-Path -LiteralPath (Join-Path $appPath $relative) -PathType Leaf) }
  }
  $backup = Join-Path $Target ('backup-code-' + $old.version + '-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff'))
  New-Item -ItemType Directory -Path $backup | Out-Null
  foreach ($record in $records) {
    if ($record.Existed) {
      $saved = Join-Path $backup $record.Relative
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $saved) | Out-Null
      Copy-Item -LiteralPath $record.Destination -Destination $saved
    }
  }
  try {
    foreach ($record in $records) {
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $record.Destination) | Out-Null
      Copy-Item -LiteralPath $record.Source -Destination $record.Destination -Force
    }
  } catch {
    foreach ($record in $records) {
      if ($record.Existed) { Copy-Item -LiteralPath (Join-Path $backup $record.Relative) -Destination $record.Destination -Force }
      elseif (Test-Path -LiteralPath $record.Destination -PathType Leaf) { Remove-Item -LiteralPath $record.Destination }
    }
    throw 'Cap nhat chua xong. Da phuc hoi ma cu; du lieu dang nhap va media van giu nguyen.'
  }
  Write-Host ('Da cap nhat len ' + $manifest.version + '. Mo Muse AI Studio.exe trong DUNG thu muc ban cu.') -ForegroundColor Green
  Write-Host 'Giu nguyen resources/app/.data: tai khoan, thu vien, prompt, khoa API va bo dem tai.'
  Write-Host ('Ban sao ma cu: ' + $backup)
} catch {
  Write-Host $_.Exception.Message -ForegroundColor Red
  exit 1
}
