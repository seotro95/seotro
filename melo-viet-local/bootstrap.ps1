$ErrorActionPreference = 'Stop'
$package = $env:MELO_VIET_PACKAGE
$action = $env:MELO_VIET_ACTION
if ($action -notin @('install','run','offline')) { throw 'Thao tac khong hop le.' }
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { throw 'Chua co WSL. Xem HUONG_DAN.txt, buoc 1.' }
$linuxPath = (& wsl.exe --distribution Ubuntu-22.04 --exec wslpath -a -u $package | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxPath) { throw 'Chua san sang Ubuntu-22.04. Xem HUONG_DAN.txt; mo Ubuntu, tao user va mat khau truoc.' }
if ($action -eq 'install') {
    & wsl.exe --distribution Ubuntu-22.04 --exec bash ($linuxPath.TrimEnd('/') + '/setup.sh')
    if ($LASTEXITCODE -ne 0) { throw 'Cai dat chua hoan tat. Giu cua so loi de kiem tra; chay lai khong xoa model/ban thu.' }
} else {
    $browser = Start-Job -ScriptBlock {
        for ($i=0; $i -lt 60; $i++) {
            try {
                $state = Invoke-RestMethod -Uri 'http://localhost:8817/api/config' -TimeoutSec 1
                if ($state.version -eq '1.0.0') { Start-Process 'http://localhost:8817/'; break }
            } catch { }
            Start-Sleep -Milliseconds 500
        }
    }
    try {
        if ($action -eq 'offline') {
            & wsl.exe --distribution Ubuntu-22.04 --exec bash ($linuxPath.TrimEnd('/') + '/start.sh') offline
        } else {
            & wsl.exe --distribution Ubuntu-22.04 --exec bash ($linuxPath.TrimEnd('/') + '/start.sh')
        }
        if ($LASTEXITCODE -ne 0) { throw 'Tool chua mo duoc. Doc loi ben tren.' }
    } finally { Stop-Job $browser -ErrorAction SilentlyContinue; Remove-Job $browser -Force -ErrorAction SilentlyContinue }
}
