# Scan only. Never run application code, alter protection settings or restore a
# quarantined file. A clear scan on this runner does not clear another device's
# detection or constitute a Microsoft false-positive decision.
$ErrorActionPreference = 'Stop'
$releaseCommit = 'ae23a93222a1b3eeb8246eb6f45e527edc08fd6c'
$archiveName = 'Hmoob-VoiceLab-1.0-source.zip'
$expectedSha = '962f0ac81867b4a84eff637a68c196b310723cd3b8a6eedc8679c15132259b1d'
$reportDir = Join-Path $env:RUNNER_TEMP 'voicelab-defender-report'
$evidenceDir = Join-Path $env:RUNNER_TEMP 'voicelab-defender-evidence'
New-Item -ItemType Directory -Force -Path $reportDir, $evidenceDir | Out-Null
$archivePath = Join-Path $evidenceDir $archiveName
$scanStarted = Get-Date
$report = [ordered]@{
    outcome = 'indeterminate'
    release_commit = $releaseCommit
    expected_sha256 = $expectedSha
    git_blob_sha256 = $null
    actual_sha256 = $null
    started_utc = $scanStarted.ToUniversalTime().ToString('o')
    runner_os = $env:RUNNER_OS
    defender_before = $null
    defender_after = $null
    archive_scanning_enabled = $null
    scan_exit_code = $null
    scan_completed_event = $false
    threat_detections = @()
    defender_events = @()
    error = $null
    limitation = 'This scan never authorizes running the withdrawn package or dismisses the reported device detection.'
}
$failure = $null
$scanInvoked = $false
($report | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath (Join-Path $reportDir 'report.json') -Encoding utf8

function Read-DefenderStatus {
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

try {
    if (-not (Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue)) {
        throw 'Windows Defender cmdlets are unavailable on this runner.'
    }
    $report.defender_before = Read-DefenderStatus
    if (-not $report.defender_before.AMServiceEnabled -or
        -not $report.defender_before.AntivirusEnabled -or
        $report.defender_before.AMRunningMode -ne 'Normal') {
        $state = $report.defender_before | ConvertTo-Json -Compress
        throw "The on-demand Defender engine is unavailable or passive. No protection settings will be changed. Status: $state"
    }
    # Real-time protection may already be off on a hosted build runner. This
    # does not disable an available on-demand engine; record it, never change it.
    $preference = Get-MpPreference -ErrorAction Stop
    $report.archive_scanning_enabled = -not $preference.DisableArchiveScanning
    if (-not $report.archive_scanning_enabled) {
        throw 'Defender archive scanning is disabled. No preferences will be changed.'
    }
    # Do not claim a clear scan if this .zip or its process/temp location is
    # excluded. Conservatively stop on exclusions rather than overriding them.
    $exclusions = @($preference.ExclusionPath) + @($preference.ExclusionExtension) + @($preference.ExclusionProcess)
    if (@($exclusions | Where-Object { $_ }).Count -gt 0) {
        $paths = @($preference.ExclusionPath) | ConvertTo-Json -Compress
        $extensions = @($preference.ExclusionExtension) | ConvertTo-Json -Compress
        $processes = @($preference.ExclusionProcess) | ConvertTo-Json -Compress
        throw "This runner has Defender exclusions; coverage is indeterminate. Paths=$paths Extensions=$extensions Processes=$processes"
    }
    Update-MpSignature -ErrorAction Stop
    $report.defender_before = Read-DefenderStatus
    $signatureTime = [datetime]::Parse($report.defender_before.AntivirusSignatureLastUpdated)
    if (((Get-Date).ToUniversalTime() - $signatureTime.ToUniversalTime()).TotalDays -gt 2) {
        throw 'Defender signatures are older than two days after the update attempt.'
    }

    # Read exact Git object bytes. PowerShell text redirection could corrupt a ZIP.
    # Nothing in the archive is extracted, imported or executed.
    $scanStarted = Get-Date
    $gitInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $gitInfo.FileName = 'git'
    $gitInfo.UseShellExecute = $false
    $gitInfo.RedirectStandardOutput = $true
    $gitInfo.RedirectStandardError = $true
    $gitInfo.ArgumentList.Add('show')
    $gitInfo.ArgumentList.Add("${releaseCommit}:$archiveName")
    $gitProcess = [System.Diagnostics.Process]::Start($gitInfo)
    $gitErrorTask = $gitProcess.StandardError.ReadToEndAsync()
    $stream = [System.IO.MemoryStream]::new()
    try {
        $gitProcess.StandardOutput.BaseStream.CopyTo($stream)
        $bytes = $stream.ToArray()
    } finally {
        $stream.Dispose()
    }
    $gitProcess.WaitForExit()
    $gitError = $gitErrorTask.GetAwaiter().GetResult()
    if ($gitProcess.ExitCode -ne 0) { throw "Could not retrieve original evidence from Git: $gitError" }
    $report.git_blob_sha256 = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    if ($report.git_blob_sha256 -ne $expectedSha) { throw 'Git evidence SHA-256 does not match the flagged release.' }
    [System.IO.File]::WriteAllBytes($archivePath, $bytes)
    if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
        throw 'Evidence disappeared during materialization; do not restore or rewrite it to bypass Defender.'
    }
    $report.actual_sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($report.actual_sha256 -ne $expectedSha) { throw 'Evidence SHA-256 does not match the flagged release.' }

    $commands = @()
    $platformDir = Join-Path $env:ProgramData 'Microsoft\Windows Defender\Platform'
    if (Test-Path -LiteralPath $platformDir) {
        $commands = @(Get-ChildItem -LiteralPath $platformDir -Directory |
            Sort-Object LastWriteTime -Descending |
            ForEach-Object { Join-Path $_.FullName 'MpCmdRun.exe' } |
            Where-Object { Test-Path -LiteralPath $_ })
    }
    if ($commands.Count -eq 0) {
        $fallback = Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
        if (Test-Path -LiteralPath $fallback) { $commands = @($fallback) }
    }
    if ($commands.Count -eq 0) { throw 'MpCmdRun.exe is unavailable on this runner.' }
    $stdout = Join-Path $reportDir 'scan-stdout.txt'
    $stderr = Join-Path $reportDir 'scan-stderr.txt'
    $scanInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $scanInfo.FileName = $commands[0]
    $scanInfo.WorkingDirectory = Split-Path -Parent $commands[0]
    $scanInfo.UseShellExecute = $false
    $scanInfo.RedirectStandardOutput = $true
    $scanInfo.RedirectStandardError = $true
    foreach ($argument in @('-Scan', '-ScanType', '3', '-File', $archivePath)) {
        $scanInfo.ArgumentList.Add($argument)
    }
    $scanInvoked = $true
    $process = [System.Diagnostics.Process]::Start($scanInfo)
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $stdoutTask.GetAwaiter().GetResult() | Set-Content -LiteralPath $stdout -Encoding utf8
    $stderrTask.GetAwaiter().GetResult() | Set-Content -LiteralPath $stderr -Encoding utf8
    $report.scan_exit_code = $process.ExitCode
} catch {
    $failure = $_.Exception.Message
    $report.error = $failure
} finally {
    try {
        if (Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue) {
            $report.defender_after = Read-DefenderStatus
            $detections = @(Get-MpThreatDetection -ErrorAction Stop | Where-Object {
                $_.InitialDetectionTime -ge $scanStarted.AddSeconds(-2) -or
                $_.LastThreatStatusChangeTime -ge $scanStarted.AddSeconds(-2)
            })
            $report.threat_detections = @($detections | Select-Object ThreatID, DetectionID,
                InitialDetectionTime, LastThreatStatusChangeTime, ActionSuccess, Resources)
        }
    } catch {
        if (-not $failure) { $failure = 'Could not collect Defender status or detection records: ' + $_.Exception.Message }
    }
    try {
        $events = @(Get-WinEvent -FilterHashtable @{
            LogName = 'Microsoft-Windows-Windows Defender/Operational'
            StartTime = $scanStarted.AddSeconds(-2)
            Id = 1000, 1001, 1002, 1005, 1116, 1117
        } -ErrorAction Stop)
        $scanIds = @()
        foreach ($event in $events) {
            if ($event.Id -ne 1000) { continue }
            $fields = @{}
            foreach ($field in ([xml]$event.ToXml()).Event.EventData.Data) {
                $fields[([string]$field.Name -replace '[^A-Za-z]', '').ToLowerInvariant()] = [string]$field.'#text'
            }
            $resources = [string]$fields['scanresources']
            if ($resources.IndexOf($archivePath, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -and $fields['scanid']) {
                $scanIds += $fields['scanid']
            }
        }
        foreach ($event in $events) {
            if ($event.Id -ne 1001) { continue }
            foreach ($field in ([xml]$event.ToXml()).Event.EventData.Data) {
                if (([string]$field.Name -replace '[^A-Za-z]', '') -ieq 'scanid' -and $scanIds -contains [string]$field.'#text') {
                    $report.scan_completed_event = $true
                }
            }
        }
        $report.defender_events = @($events | Select-Object Id, TimeCreated, Message)
    } catch {
        if (-not $failure) { $failure = 'Defender completion/detection events could not be collected: ' + $_.Exception.Message }
    }

    $foundThreat = $report.threat_detections.Count -gt 0 -or
        @($report.defender_events | Where-Object { $_.Id -in 1116, 1117 }).Count -gt 0
    $scanFailed = @($report.defender_events | Where-Object { $_.Id -in 1002, 1005 }).Count -gt 0
    if ($foundThreat) {
        $report.outcome = 'detection-reported'
    } elseif (-not $failure -and $scanInvoked -and $report.scan_exit_code -eq 0 -and
        $report.scan_completed_event -and -not $scanFailed -and
        $report.actual_sha256 -eq $expectedSha -and
        $report.defender_after.AMServiceEnabled -and $report.defender_after.AntivirusEnabled -and
        $report.defender_after.AMRunningMode -eq 'Normal') {
        $report.outcome = 'no-detection-on-this-runner'
    } else {
        $report.outcome = 'indeterminate'
    }
    if ($failure) { $report.error = $failure }
    $report.finished_utc = (Get-Date).ToUniversalTime().ToString('o')
    $json = $report | ConvertTo-Json -Depth 10
    $json | Set-Content -LiteralPath (Join-Path $reportDir 'report.json') -Encoding utf8
    Write-Output $json
    $summary = @"
## VoiceLab Defender investigation

Outcome: **$($report.outcome)**

Original archive SHA-256: ``$expectedSha``

Error or limitation: $($report.error)

The original ZIP is not uploaded as an artifact. No application code or installer ran.
This result does not authorize restoring/running the withdrawn package or establish a false positive.
"@
    if ($env:GITHUB_STEP_SUMMARY) { $summary | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY }
    if ($report.outcome -ne 'no-detection-on-this-runner') {
        $detail = if ($report.error) { [string]$report.error } else { 'Threat detections or insufficient scan-completion evidence; inspect report.json.' }
        $detail = $detail.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
        Write-Output "::error title=Defender investigation - $($report.outcome)::$detail"
    }
}

if ($report.outcome -eq 'detection-reported') { exit 2 }
if ($report.outcome -ne 'no-detection-on-this-runner') { exit 1 }
