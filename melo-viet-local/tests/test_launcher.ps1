$ErrorActionPreference = 'Stop'
trap {
    Write-Host ('::error title=Windows launcher test::' + $_.Exception.Message + ' at ' + ($_.ScriptStackTrace -replace "`r?`n", ' | '))
    throw
}
$launcher = Join-Path (Split-Path $PSScriptRoot -Parent) 'bootstrap.ps1'
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('melo-launcher-' + [guid]::NewGuid())
$null = New-Item -Path $testRoot -ItemType Directory
$package = Join-Path $testRoot ('Melo folder ' + [char]0x1ec7)
$null = New-Item -Path $package -ItemType Directory
$oldPackage = $env:MELO_VIET_PACKAGE
$oldAction = $env:MELO_VIET_ACTION
$oldDistro = $env:MELO_VIET_DISTRO
function global:wsl.exe {
    $global:meloTestWsCalls.Add(@($args))
    $global:LASTEXITCODE = 0
    if ($args[0] -eq '--list') { return $global:meloTestNames }
    if ($args[3] -eq 'cat') {
        if ($global:meloTestLaunchFail) { $global:LASTEXITCODE = 1; return }
        return @('ID=ubuntu',('VERSION_ID="' + $global:meloTestOsVersion + '"'))
    }
    if ($args[3] -eq 'wslpath') {
        if ($global:meloTestPathFail) { $global:LASTEXITCODE = 1; return }
        return '/mnt/c/Melo folder test'
    }
    if ($args[3] -eq 'bash') {
        if ($global:meloTestInstallFail) { $global:LASTEXITCODE = 1 }
        return
    }
    throw ('Unexpected WSL arguments: ' + ($args -join ' '))
}
function Reset-Case {
    $global:meloTestWsCalls = New-Object 'System.Collections.Generic.List[object]'
    $global:meloTestNames = @('Ubuntu')
    $global:meloTestOsVersion = '22.04'
    $global:meloTestPathFail = $false
    $global:meloTestLaunchFail = $false
    $global:meloTestInstallFail = $false
    $env:MELO_VIET_PACKAGE = $package + '\'
    $env:MELO_VIET_ACTION = 'install'
    $env:MELO_VIET_DISTRO = ''
    Remove-Item -LiteralPath (Join-Path $package 'wsl-distro.txt') -ErrorAction SilentlyContinue
}
function Assert-True($value, $message) { if (-not $value) { throw $message } }
function Expect-Failure($expected) {
    $message = $null
    try { & $launcher } catch { $message = $_.Exception.Message }
    Assert-True ($message -like ('*' + $expected + '*')) ('Expected failure: ' + $expected + '; got: ' + $message)
    Assert-True (@($global:meloTestWsCalls | Where-Object { $_[3] -eq 'bash' }).Count -eq 0) 'A rejected distribution must not run setup.sh'
}
try {
    Reset-Case
    & $launcher
    $call = $global:meloTestWsCalls[$global:meloTestWsCalls.Count - 1]
    Assert-True ($call[1] -eq 'Ubuntu') 'Must use existing Ubuntu registration, not a hardcoded suffix'
    Assert-True ($call[4] -eq '/mnt/c/Melo folder test/setup.sh') 'Path with spaces must be one argument'
    $pathCall = @($global:meloTestWsCalls | Where-Object { $_[3] -eq 'wslpath' })[0]
    Assert-True ($pathCall[6] -eq $package) 'Trailing Windows slash must be removed without losing Unicode or spaces'
    Assert-True ((Get-Content -LiteralPath (Join-Path $package 'wsl-distro.txt') -Raw).Trim() -eq 'Ubuntu') 'Selected distro must persist'

    Reset-Case
    $global:meloTestNames = @('docker-desktop', 'Ubuntu', 'Ubuntu-22.04')
    & $launcher
    Assert-True ($global:meloTestWsCalls[1][1] -eq 'Ubuntu-22.04') 'Prefer explicit installed 22.04 registration'

    Reset-Case
    $global:meloTestNames = @(('Ubuntu'.ToCharArray() -join "`0") + "`0`r")
    & $launcher
    Assert-True ($global:meloTestWsCalls[1][1] -eq 'Ubuntu') 'Decode NUL-padded WSL names'

    Reset-Case
    $global:meloTestNames = @('Ubuntu', 'My Ubuntu')
    $env:MELO_VIET_DISTRO = 'My Ubuntu'
    & $launcher
    Assert-True ($global:meloTestWsCalls[1][1] -eq 'My Ubuntu') 'Explicit override must select the exact installed name'

    Reset-Case
    $global:meloTestNames = @('Ubuntu', 'Saved Ubuntu')
    Set-Content -LiteralPath (Join-Path $package 'wsl-distro.txt') -Value 'Saved Ubuntu' -Encoding UTF8
    & $launcher
    Assert-True ($global:meloTestWsCalls[1][1] -eq 'Saved Ubuntu') 'Subsequent launches must reuse saved distro'

    Reset-Case
    $env:MELO_VIET_DISTRO = 'Missing'
    Expect-Failure 'Khong tim thay WSL'

    Reset-Case
    $global:meloTestNames = @('docker-desktop')
    Expect-Failure 'Chua tim thay Ubuntu'

    Reset-Case
    $global:meloTestOsVersion = '24.04'
    Expect-Failure 'khong phai Ubuntu 22.04'

    Reset-Case
    $global:meloTestLaunchFail = $true
    Expect-Failure 'Khong mo duoc WSL'

    Reset-Case
    $global:meloTestPathFail = $true
    Expect-Failure 'Khong doi duoc duong dan'

    Reset-Case
    $global:meloTestInstallFail = $true
    $message = $null
    try { & $launcher } catch { $message = $_.Exception.Message }
    Assert-True ($message -like '*Cai dat chua hoan tat*') 'Installer failure must not report success'

    Reset-Case
    $env:MELO_VIET_ACTION = 'update'
    & $launcher
    Assert-True ($global:meloTestWsCalls[$global:meloTestWsCalls.Count-1][5] -eq '--update') 'Fast update must not request full model installation'

    Reset-Case
    $env:MELO_VIET_ACTION = 'install-online'
    & $launcher
    Assert-True ($global:meloTestWsCalls[$global:meloTestWsCalls.Count-1][5] -eq '--online-only') 'Online-only installation must not install the offline SDKs'

    Write-Host '13 Windows PowerShell launcher cases passed with mocked WSL; no Linux distribution was installed or modified.'
} finally {
    Remove-Item Function:\wsl.exe -ErrorAction SilentlyContinue
    Remove-Variable -Name meloTestWsCalls,meloTestNames,meloTestOsVersion,meloTestPathFail,meloTestLaunchFail,meloTestInstallFail -Scope Global -ErrorAction SilentlyContinue
    $env:MELO_VIET_PACKAGE = $oldPackage
    $env:MELO_VIET_ACTION = $oldAction
    $env:MELO_VIET_DISTRO = $oldDistro
    Remove-Item -LiteralPath $testRoot -Recurse -Force
}

# Expected negative cases set LASTEXITCODE=1 in the mock. Do not leak that
# code into the Actions PowerShell wrapper after all assertions passed.
$global:LASTEXITCODE = 0
Write-Host '::notice title=Windows launcher tests::13 cases passed on Windows PowerShell 5.1 with mocked WSL.'
