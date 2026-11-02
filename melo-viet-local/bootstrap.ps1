$ErrorActionPreference = 'Stop'
# Decode UTF-8 paths from Linux correctly in Windows PowerShell 5.1.
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$package = $env:MELO_VIET_PACKAGE
$action = $env:MELO_VIET_ACTION
if ($action -notin @('install','install-online','install-fast','update','run','offline')) { throw 'Thao tac khong hop le.' }
if (-not $package -or -not (Test-Path -LiteralPath $package -PathType Container)) { throw 'Khong tim thay thu muc bo cai. Hay giai nen toan bo ZIP truoc.' }
# A trailing backslash can escape the closing quote in native Windows arguments.
if ($package.Length -gt 3) { $package = $package.TrimEnd('\','/') }
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'Chua co WSL. Xem HUONG_DAN.txt, buoc 1.' }
$rawNames = @(& wsl.exe --list --quiet)
if ($LASTEXITCODE -ne 0) { throw 'Khong doc duoc danh sach WSL. Thu chay wsl --list --verbose trong PowerShell.' }
# Some Windows/WSL versions pipe UTF-16 names with embedded NUL characters.
$names = @(($rawNames -join "`n").Replace("`0",'') -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$choiceFile = Join-Path $package 'wsl-distro.txt'
$distribution = $env:MELO_VIET_DISTRO
if (-not $distribution -and (Test-Path -LiteralPath $choiceFile)) { $distribution = (Get-Content -LiteralPath $choiceFile -Raw).Trim() }
if ($distribution) {
    if ($distribution -notin $names) { throw "Khong tim thay WSL '$distribution'. Kiem tra wsl --list --verbose; sua wsl-distro.txt hoac MELO_VIET_DISTRO." }
} elseif ('Ubuntu-22.04' -in $names) {
    $distribution = 'Ubuntu-22.04'
} elseif ('Ubuntu' -in $names) {
    $distribution = 'Ubuntu'
} else {
    throw 'Chua tim thay Ubuntu. Xem wsl --list --verbose. Neu Ubuntu da doi ten, dat ten vao wsl-distro.txt trong thu muc bo cai.'
}
Write-Host "Dang dung WSL: $distribution"
$osRelease = (& wsl.exe --distribution $distribution --exec cat /etc/os-release | Out-String).Replace("`0",'')
if ($LASTEXITCODE -ne 0) { throw "Khong mo duoc WSL '$distribution'. Chay wsl -d $distribution de xem loi va hoan tat tao user Linux neu duoc hoi." }
if ($osRelease -notmatch '(?m)^ID="?ubuntu"?\s*$' -or $osRelease -notmatch '(?m)^VERSION_ID="?22\.04"?\s*$') {
    throw "WSL '$distribution' khong phai Ubuntu 22.04. Bo cai nay can Ubuntu 22.04 / Python 3.10. Khong xoa hoac nang cap ban Linux dang co. Xem HUONG_DAN.txt."
}
$linuxPath = (& wsl.exe --distribution $distribution --exec wslpath -a -u $package | Out-String).Replace("`0",'').Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxPath.StartsWith('/')) { throw "Khong doi duoc duong dan bo cai sang Linux. Giai nen ZIP vao thu muc tren o C: hoac D: va chay lai. WSL: $distribution" }
Set-Content -LiteralPath $choiceFile -Value $distribution -Encoding UTF8
if ($action -in @('install','install-online','install-fast','update')) {
    $mode = '--install'
    if ($action -eq 'update') { $mode = '--update' }
    if ($action -eq 'install-online') { $mode = '--online-only' }
    if ($action -eq 'install-fast') { $mode = '--fast-only' }
    & wsl.exe --distribution $distribution --exec bash ($linuxPath.TrimEnd('/') + '/setup.sh') $mode
    if ($LASTEXITCODE -ne 0) { throw 'Cai dat chua hoan tat. Giu cua so loi de kiem tra; chay lai khong xoa model/ban thu.' }
} else {
    $browser = Start-Job -ScriptBlock {
        for ($i=0; $i -lt 60; $i++) {
            try {
                $state = Invoke-RestMethod -Uri 'http://localhost:8817/api/config' -TimeoutSec 1
                if ($state.version -eq '1.2.0') { Start-Process 'http://localhost:8817/'; break }
            } catch { }
            Start-Sleep -Milliseconds 500
        }
    }
    try {
        if ($action -eq 'offline') {
            & wsl.exe --distribution $distribution --exec bash ($linuxPath.TrimEnd('/') + '/start.sh') offline
        } else {
            & wsl.exe --distribution $distribution --exec bash ($linuxPath.TrimEnd('/') + '/start.sh')
        }
        if ($LASTEXITCODE -ne 0) { throw 'Tool chua mo duoc. Doc loi ben tren.' }
    } finally { Stop-Job $browser -ErrorAction SilentlyContinue; Remove-Job $browser -Force -ErrorAction SilentlyContinue }
}
