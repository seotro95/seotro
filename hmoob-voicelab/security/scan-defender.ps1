# Isolated investigation only. Never execute the app, change Defender settings,
# restore quarantined files, or upload the evidence archive.
$ErrorActionPreference = 'Stop'
$release = 'ae23a93222a1b3eeb8246eb6f45e527edc08fd6c'
$name = 'Hmoob-VoiceLab-1.0-source.zip'
$sha = '962f0ac81867b4a84eff637a68c196b310723cd3b8a6eedc8679c15132259b1d'
$reference = 'https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus'
$reportDir = Join-Path $env:RUNNER_TEMP 'voicelab-defender-report'
$evidenceDir = Join-Path $env:ProgramData ('VoiceLabSecurityReview-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $reportDir, $evidenceDir | Out-Null
$archive = Join-Path $evidenceDir $name
$started = Get-Date
$report = [ordered]@{
    outcome = 'indeterminate'
    release_commit = $release
    expected_sha256 = $sha
    git_blob_sha256 = $null
    actual_sha256 = $null
    scan_scope = 'original-zip-analysis'
    started_utc = $started.ToUniversalTime().ToString('o')
    defender_before = $null
    defender_after = $null
    signature_verified = $false
    installed_help_verified = $false
    official_reference = $reference
    reference_semantics_verified = $false
    scan_exit_code = $null
    scan_console_completed = $false
    threat_detections = @()
    error = $null
    limitation = 'No result dismisses the reported device detection or authorizes restoring, running, or redistributing the withdrawn ZIP.'
}
($report | ConvertTo-Json -Depth 10) | Set-Content (Join-Path $reportDir 'report.json') -Encoding utf8

function Invoke-ReadOnlyProcess([string] $exe, [string[]] $arguments) {
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $exe
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $arguments) { $info.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::Start($info)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    return [pscustomobject]@{
        Code = $process.ExitCode
        Out = $stdoutTask.GetAwaiter().GetResult()
        Err = $stderrTask.GetAwaiter().GetResult()
    }
}

function Read-Status {
    $s = Get-MpComputerStatus -ErrorAction Stop
    return [ordered]@{
        AMServiceEnabled = $s.AMServiceEnabled
        AntivirusEnabled = $s.AntivirusEnabled
        RealTimeProtectionEnabled = $s.RealTimeProtectionEnabled
        AMRunningMode = [string]$s.AMRunningMode
        AMEngineVersion = [string]$s.AMEngineVersion
        AMProductVersion = [string]$s.AMProductVersion
        AntivirusSignatureVersion = [string]$s.AntivirusSignatureVersion
        AntivirusSignatureLastUpdated = $s.AntivirusSignatureLastUpdated.ToUniversalTime().ToString('o')
    }
}

$scan = $null
try {
    $report.defender_before = Read-Status
    if (-not $report.defender_before.AMServiceEnabled -or
        -not $report.defender_before.AntivirusEnabled -or
        $report.defender_before.AMRunningMode -ne 'Normal') {
        throw ('The on-demand engine is unavailable: ' + ($report.defender_before | ConvertTo-Json -Compress))
    }
    Update-MpSignature -ErrorAction Stop
    $report.defender_before = Read-Status
    $signatureTime = [datetime]::Parse($report.defender_before.AntivirusSignatureLastUpdated)
    if (((Get-Date).ToUniversalTime() - $signatureTime.ToUniversalTime()).TotalDays -gt 2) {
        throw 'Signature update did not produce definitions less than two days old.'
    }

    $platform = Join-Path $env:ProgramData 'Microsoft\Windows Defender\Platform'
    $commands = @()
    if (Test-Path $platform) {
        $commands = @(Get-ChildItem $platform -Directory | Sort-Object LastWriteTime -Descending |
            ForEach-Object { Join-Path $_.FullName 'MpCmdRun.exe' } | Where-Object { Test-Path $_ })
    }
    if (-not $commands.Count) {
        $fallback = Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
        if (Test-Path $fallback) { $commands = @($fallback) }
    }
    if (-not $commands.Count) { throw 'MpCmdRun.exe is unavailable.' }
    $command = $commands[0]
    $signature = Get-AuthenticodeSignature -LiteralPath $command
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft') {
        throw 'The installed scanner does not have a valid Microsoft Authenticode signature.'
    }
    $report.signature_verified = $true
    $help = Invoke-ReadOnlyProcess $command @('-?')
    ($help.Out + $help.Err) | Set-Content (Join-Path $reportDir 'installed-scanner-help.txt') -Encoding utf8
    $report.installed_help_verified = ($help.Out + $help.Err) -match '-DisableRemediation'
    if (-not $report.installed_help_verified) { throw 'The installed scanner does not document analysis mode.' }

    # The hosted image excludes build drives and disables normal archive scans.
    # Verify official semantics before using a per-scan analysis option. This
    # increases scan coverage without modifying preferences/exclusions/protection.
    $page = Invoke-WebRequest -Uri $reference -TimeoutSec 45 -MaximumRedirection 5
    $plain = [System.Net.WebUtility]::HtmlDecode(($page.Content -replace '(?s)<script.*?</script>', ' ' -replace '<[^>]+>', ' '))
    $plain = $plain -replace '\s+', ' '
    $plain | Set-Content (Join-Path $reportDir 'official-reference-text.txt') -Encoding utf8
    $referenceSnippet = 'The analysis option was not found in the returned document.'
    foreach ($match in [regex]::Matches($plain, '-DisableRemediation', 'IgnoreCase')) {
        $section = $plain.Substring($match.Index, [Math]::Min(4500, $plain.Length - $match.Index))
        $referenceSnippet = $section
        if ($section -match 'File(?: and folder)? exclusions are ignored' -and
            $section -match 'Archive files are scanned' -and
            $section -match "Actions (?:are not|aren['’]t) applied") {
            $report.reference_semantics_verified = $true
            $section | Set-Content (Join-Path $reportDir 'official-analysis-mode-reference.txt') -Encoding utf8
            break
        }
    }
    if (-not $report.reference_semantics_verified) {
        throw ('Analysis mode semantics could not be verified from current official Microsoft documentation. Official excerpt: ' + $referenceSnippet)
    }

    # Read the original Git blob as bytes, never through text redirection.
    $gitInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $gitInfo.FileName = 'git'
    $gitInfo.UseShellExecute = $false
    $gitInfo.RedirectStandardOutput = $true
    $gitInfo.RedirectStandardError = $true
    $gitInfo.ArgumentList.Add('show')
    $gitInfo.ArgumentList.Add($release + ':' + $name)
    $git = [System.Diagnostics.Process]::Start($gitInfo)
    $gitErrorTask = $git.StandardError.ReadToEndAsync()
    $memory = [System.IO.MemoryStream]::new()
    try { $git.StandardOutput.BaseStream.CopyTo($memory); $bytes = $memory.ToArray() }
    finally { $memory.Dispose() }
    $git.WaitForExit()
    if ($git.ExitCode -ne 0) { throw ('Git evidence read failed: ' + $gitErrorTask.GetAwaiter().GetResult()) }
    $report.git_blob_sha256 = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    if ($report.git_blob_sha256 -ne $sha) { throw 'Original Git evidence hash mismatch.' }
    [System.IO.File]::WriteAllBytes($archive, $bytes)
    $report.actual_sha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($report.actual_sha256 -ne $sha) { throw 'Materialized evidence hash mismatch. Never restore/rewrite to bypass a quarantine.' }

    # This applies to this isolated custom scan only: no remediation, while
    # exclusions are ignored and archives are inspected per verified vendor docs.
    # It neither disables antivirus nor permits executing any archive contents.
    $scan = Invoke-ReadOnlyProcess $command @('-Scan', '-ScanType', '3', '-File', $archive, '-DisableRemediation')
    $scan.Out | Set-Content (Join-Path $reportDir 'scan-stdout.txt') -Encoding utf8
    $scan.Err | Set-Content (Join-Path $reportDir 'scan-stderr.txt') -Encoding utf8
    $report.scan_exit_code = $scan.Code
    $report.scan_console_completed = $scan.Out -match '(?i)scan finished'
    $report.defender_after = Read-Status
    # Vendor-documented analysis mode does not publish normal detection events.
    # No event is therefore used as evidence that a scan was clear.
    try {
        $report.threat_detections = @(Get-MpThreatDetection | Where-Object {
            $_.InitialDetectionTime -ge $started.AddSeconds(-2) -or
            $_.LastThreatStatusChangeTime -ge $started.AddSeconds(-2)
        } | Select-Object ThreatID, InitialDetectionTime, LastThreatStatusChangeTime, Resources)
    } catch { }

    $consoleThreat = ($scan.Out + $scan.Err) -match '(?i)(Trojan|Virus|Worm|Backdoor|Ransom|HackTool|PUA|Exploit|Behavior|SoftwareBundler):|(?:found|detected)\s*[=:]?\s*[1-9]\d*\s*threat'
    if ($consoleThreat -or $report.threat_detections.Count -gt 0) {
        $report.outcome = 'detection-reported'
    } elseif ($scan.Code -eq 0 -and $report.scan_console_completed -and
        $report.defender_after.AMServiceEnabled -and $report.defender_after.AntivirusEnabled -and
        $report.defender_after.AMRunningMode -eq 'Normal') {
        $report.outcome = 'no-detection-on-this-runner'
    } else {
        throw ('Scan did not establish a no-detection result; native exit code ' + $scan.Code)
    }
} catch {
    $report.error = $_.Exception.Message
} finally {
    $report.finished_utc = (Get-Date).ToUniversalTime().ToString('o')
    ($report | ConvertTo-Json -Depth 10) | Set-Content (Join-Path $reportDir 'report.json') -Encoding utf8
    $console = if ($scan) { ($scan.Out + $scan.Err) } else { '' }
    if ($console.Length -gt 5000) { $console = $console.Substring(0, 5000) }
    $message = 'Outcome=' + $report.outcome + '; native exit=' + $report.scan_exit_code +
        '; error=' + $report.error + '; scanner output=' + $console
    $message = $message.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    if ($report.outcome -eq 'no-detection-on-this-runner') {
        Write-Output "::notice title=Defender analysis result::$message"
    } else {
        Write-Output "::error title=Defender analysis result::$message"
    }
    $summary = @"
## Defender investigation: $($report.outcome)
- Original ZIP SHA-256: $sha
- Scope: original ZIP, isolated custom analysis scan, no application execution.
- Scanner signature verified: $($report.signature_verified)
- Vendor analysis-mode semantics verified: $($report.reference_semantics_verified)
- Native exit code: $($report.scan_exit_code)
- Error: $($report.error)

The user-device detection remains unresolved. Do not restore, run or redistribute the withdrawn ZIP.
No evidence ZIP is uploaded; only reports and official scanner/reference text are retained.
"@
    if ($env:GITHUB_STEP_SUMMARY) { $summary | Add-Content $env:GITHUB_STEP_SUMMARY }
}
if ($report.outcome -eq 'detection-reported') { exit 2 }
if ($report.outcome -ne 'no-detection-on-this-runner') { exit 1 }
