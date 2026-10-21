[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $PackageRoot,
    [Parameter(Mandatory = $true)][string] $Archive,
    [Parameter(Mandatory = $true)][string] $ReportDirectory,
    [ValidateRange(60, 1800)][int] $ScanTimeoutSeconds = 900
)

# This gate scans a newly built package. It does not change Defender preferences,
# exclusions or protection, restore files, or dismiss the old user-device alert.
$ErrorActionPreference = 'Stop'
$reference = 'https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus'
$started = Get-Date
$reportDir = [System.IO.Path]::GetFullPath($ReportDirectory)
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$report = [ordered]@{
    outcome = 'indeterminate'
    source_commit = $env:GITHUB_SHA
    started_utc = $started.ToUniversalTime().ToString('o')
    finished_utc = $null
    package_root = $null
    package_file_count = $null
    archive = $null
    archive_sha256_before = $null
    archive_sha256_after = $null
    defender_before = $null
    defender_after = $null
    scanner_path = $null
    scanner_signature_verified = $false
    installed_help_verified = $false
    official_reference = $reference
    reference_semantics_verified = $false
    scans = @()
    recent_package_detections = @()
    error = $null
    limitation = 'No detection on this runner is not Microsoft clearance or a resolution of the earlier user-device alert. The withdrawn original ZIP is not restored or republished.'
}

function Save-Report {
    ($report | ConvertTo-Json -Depth 12) |
        Set-Content -LiteralPath (Join-Path $reportDir 'report.json') -Encoding utf8
}

function Invoke-ScannerProcess([string] $Executable, [string[]] $Arguments, [int] $TimeoutSeconds) {
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Executable
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::Start($info)
    try {
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $timedOut = $false
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            # Stop only the spawned command, never the Defender service.
            $timedOut = $true
            $process.Kill($true)
            $process.WaitForExit()
        }
        return [pscustomobject]@{
            Code = $process.ExitCode
            Out = $stdoutTask.GetAwaiter().GetResult()
            Err = $stderrTask.GetAwaiter().GetResult()
            TimedOut = $timedOut
        }
    } finally {
        $process.Dispose()
    }
}

function Read-DefenderStatus {
    $status = Get-MpComputerStatus -ErrorAction Stop
    return [ordered]@{
        AMServiceEnabled = $status.AMServiceEnabled
        AntivirusEnabled = $status.AntivirusEnabled
        RealTimeProtectionEnabled = $status.RealTimeProtectionEnabled
        AMRunningMode = [string]$status.AMRunningMode
        AMEngineVersion = [string]$status.AMEngineVersion
        AMProductVersion = [string]$status.AMProductVersion
        AntivirusSignatureVersion = [string]$status.AntivirusSignatureVersion
        AntivirusSignatureLastUpdated = $status.AntivirusSignatureLastUpdated.ToUniversalTime().ToString('o')
    }
}

function Assert-DefenderReady($Status) {
    if (-not $Status.AMServiceEnabled -or -not $Status.AntivirusEnabled -or
        $Status.AMRunningMode -ne 'Normal') {
        throw ('The on-demand Defender engine is unavailable: ' + ($Status | ConvertTo-Json -Compress))
    }
    $signatureTime = [datetime]::Parse($Status.AntivirusSignatureLastUpdated).ToUniversalTime()
    if (((Get-Date).ToUniversalTime() - $signatureTime).TotalDays -gt 2) {
        throw 'Defender definitions are more than two days old.'
    }
}

function Find-SignedScanner {
    $platform = Join-Path $env:ProgramData 'Microsoft\Windows Defender\Platform'
    $commands = @()
    if (Test-Path -LiteralPath $platform) {
        $commands = @(Get-ChildItem -LiteralPath $platform -Directory |
            Sort-Object LastWriteTime -Descending |
            ForEach-Object { Join-Path $_.FullName 'MpCmdRun.exe' } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
    }
    if (-not $commands.Count) {
        $fallback = Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
        if (Test-Path -LiteralPath $fallback -PathType Leaf) { $commands = @($fallback) }
    }
    if (-not $commands.Count) { throw 'MpCmdRun.exe is unavailable.' }
    $command = $commands[0]
    $signature = Get-AuthenticodeSignature -LiteralPath $command
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft') {
        throw 'The installed scanner lacks a valid Microsoft Authenticode signature.'
    }
    return $command
}

function Assert-AnalysisSemantics([string] $Command) {
    $help = Invoke-ScannerProcess $Command @('-?') 60
    ($help.Out + $help.Err) |
        Set-Content -LiteralPath (Join-Path $reportDir 'installed-scanner-help.txt') -Encoding utf8
    if ($help.TimedOut) { throw 'The installed scanner help command timed out.' }
    $report.installed_help_verified = ($help.Out + $help.Err) -match '-DisableRemediation'
    if (-not $report.installed_help_verified) { throw 'The installed scanner does not document analysis mode.' }

    # Hosted images have build-drive exclusions and ordinary archive scanning
    # disabled. Confirm this per-scan option expands coverage without changing
    # preferences or protection before using it.
    $page = Invoke-WebRequest -Uri $reference -TimeoutSec 45 -MaximumRedirection 5
    $plain = [System.Net.WebUtility]::HtmlDecode(($page.Content -replace '(?s)<script.*?</script>', ' ' -replace '<[^>]+>', ' '))
    $plain = $plain -replace '\s+', ' '
    $plain | Set-Content -LiteralPath (Join-Path $reportDir 'official-reference-text.txt') -Encoding utf8
    foreach ($match in [regex]::Matches($plain, '-DisableRemediation', 'IgnoreCase')) {
        $section = $plain.Substring($match.Index, [Math]::Min(4500, $plain.Length - $match.Index))
        if ($section -match 'File(?: and folder)? exclusions are ignored' -and
            $section -match 'Archive files are scanned' -and
            $section -match "Actions (?:are not|aren['’]t) applied") {
            $report.reference_semantics_verified = $true
            $section | Set-Content -LiteralPath (Join-Path $reportDir 'official-analysis-mode-reference.txt') -Encoding utf8
            break
        }
    }
    if (-not $report.reference_semantics_verified) {
        throw 'Current Microsoft documentation did not establish the required analysis-mode semantics.'
    }
}

function Scan-Target([string] $Command, [string] $Label, [string] $Target) {
    $scan = Invoke-ScannerProcess $Command @('-Scan', '-ScanType', '3', '-File', $Target, '-DisableRemediation') $ScanTimeoutSeconds
    $scan.Out | Set-Content -LiteralPath (Join-Path $reportDir ($Label + '-stdout.txt')) -Encoding utf8
    $scan.Err | Set-Content -LiteralPath (Join-Path $reportDir ($Label + '-stderr.txt')) -Encoding utf8
    $console = $scan.Out + $scan.Err
    $threat = $console -match '(?i)(Trojan|Virus|Worm|Backdoor|Ransom|HackTool|PUA|Exploit|Behavior|SoftwareBundler):|(?:found|detected)\s*[=:]?\s*[1-9]\d*\s*threat'
    $entry = [ordered]@{
        label = $Label
        target = $Target
        exit_code = $scan.Code
        timed_out = $scan.TimedOut
        console_completed = [bool]($console -match '(?i)scan finished')
        explicit_no_threats = [bool]($console -match '(?i)found no threats|no threats (?:were )?(?:found|detected)')
        console_threat = [bool]$threat
        outcome = 'indeterminate'
    }
    if ($threat) {
        $entry.outcome = 'detection-reported'
    } elseif (-not $scan.TimedOut -and $scan.Code -eq 0 -and $entry.console_completed -and $entry.explicit_no_threats) {
        $entry.outcome = 'no-detection-on-this-runner'
    }
    $report.scans += $entry
    Save-Report
    return $entry
}

Save-Report
try {
    if (-not $IsWindows) { throw 'Run the Defender gate on native Windows with PowerShell 7.' }
    $root = (Get-Item -LiteralPath $PackageRoot -ErrorAction Stop).FullName
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw 'PackageRoot must be a directory.' }
    $archivePath = (Get-Item -LiteralPath $Archive -ErrorAction Stop).FullName
    if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) { throw 'Archive must be a file.' }
    $rootPrefix = $root.TrimEnd([char[]]'\/') + [System.IO.Path]::DirectorySeparatorChar
    if ($reportDir.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or
        $reportDir.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Reports must be outside the package being scanned.'
    }
    $report.package_root = $root
    $report.archive = $archivePath
    $report.archive_sha256_before = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -Force -File)
    if (-not $files.Count) { throw 'Refuse to scan an empty package.' }
    if (@(Get-ChildItem -LiteralPath $root -Recurse -Force |
        Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint }).Count) {
        throw 'Portable package must contain materialized files, not reparse points.'
    }
    $report.package_file_count = $files.Count
    $inventory = @($files | ForEach-Object {
        [ordered]@{
            path = [System.IO.Path]::GetRelativePath($root, $_.FullName)
            bytes = $_.Length
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
    ($inventory | ConvertTo-Json -Depth 4) |
        Set-Content -LiteralPath (Join-Path $reportDir 'package-inventory.json') -Encoding utf8

    $report.defender_before = Read-DefenderStatus
    # Freshen signatures only; this does not modify the protection configuration.
    Update-MpSignature -ErrorAction Stop
    $report.defender_before = Read-DefenderStatus
    Assert-DefenderReady $report.defender_before
    $command = Find-SignedScanner
    $report.scanner_path = $command
    $report.scanner_signature_verified = $true
    Assert-AnalysisSemantics $command
    Save-Report

    $folderScan = Scan-Target $command 'extracted-package' $root
    if ($folderScan.outcome -eq 'detection-reported') {
        $report.outcome = 'detection-reported'
        throw 'Defender detected content in the extracted package; no artifact may be published.'
    }
    if ($folderScan.outcome -ne 'no-detection-on-this-runner') {
        throw 'The extracted-package scan did not establish a completed no-detection result.'
    }
    $zipScan = Scan-Target $command 'completed-archive' $archivePath
    if ($zipScan.outcome -eq 'detection-reported') {
        $report.outcome = 'detection-reported'
        throw 'Defender detected content in the completed archive; no artifact may be published.'
    }
    if ($zipScan.outcome -ne 'no-detection-on-this-runner') {
        throw 'The archive scan did not establish a completed no-detection result.'
    }

    $report.defender_after = Read-DefenderStatus
    Assert-DefenderReady $report.defender_after
    $report.archive_sha256_after = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($report.archive_sha256_before -ne $report.archive_sha256_after) {
        throw 'Archive changed during the scan; do not restore or rewrite any removed file.'
    }
    # Analysis mode need not publish ordinary detection events. Absence of events
    # is never used as evidence; an explicit package event still blocks upload.
    try {
        $pathPattern = [regex]::Escape($root) + '|' + [regex]::Escape($archivePath)
        $report.recent_package_detections = @(Get-MpThreatDetection | Where-Object {
            ($_.InitialDetectionTime -ge $started.AddSeconds(-2) -or
             $_.LastThreatStatusChangeTime -ge $started.AddSeconds(-2)) -and
            (($_.Resources -join ' ') -match $pathPattern)
        } | Select-Object ThreatID, InitialDetectionTime, LastThreatStatusChangeTime, Resources)
    } catch { }
    if ($report.recent_package_detections.Count -gt 0) {
        $report.outcome = 'detection-reported'
        throw 'Defender recorded a package detection; no artifact may be published.'
    }
    $report.outcome = 'no-detection-on-this-runner'
} catch {
    $report.error = $_.Exception.Message
} finally {
    $report.finished_utc = (Get-Date).ToUniversalTime().ToString('o')
    Save-Report
    $message = ('Outcome=' + $report.outcome + '; package files=' + $report.package_file_count +
        '; archive SHA256=' + $report.archive_sha256_after + '; error=' + $report.error)
    $message = $message.Replace('%', '%25').Replace("`r", '%0D').Replace("`n", '%0A')
    if ($report.outcome -eq 'no-detection-on-this-runner') {
        Write-Output "::notice title=Portable Defender gate::$message"
    } else {
        Write-Output "::error title=Portable Defender gate::$message"
    }
    if ($env:GITHUB_STEP_SUMMARY) {
        @"
## Portable Defender gate: $($report.outcome)
- Scope: all files in the extracted new package and its completed ZIP.
- Package file count: $($report.package_file_count)
- Archive SHA-256: $($report.archive_sha256_after)
- Signed Microsoft scanner: $($report.scanner_signature_verified)
- Current vendor analysis-mode semantics verified: $($report.reference_semantics_verified)
- Error: $($report.error)

No Defender protection setting or exclusion was changed. The old user-device
detection remains unresolved; this result describes only the new files on this runner.
"@ | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
    }
}
if ($report.outcome -eq 'detection-reported') { exit 2 }
if ($report.outcome -ne 'no-detection-on-this-runner') { exit 1 }
exit 0
