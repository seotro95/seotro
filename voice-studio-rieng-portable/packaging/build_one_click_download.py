"""Generate one readable Windows download command for a verified full ZIP.

The command is a downloader, not the 4.72 GB application itself. It downloads
only fixed HTTPS release assets, verifies each piece and the complete ZIP, and
never executes downloaded code. Windows' built-in PowerShell handles hashes;
curl.exe resumes partial downloads when available, with WebClient as fallback.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


DEFAULT_BASE = 'https://github.com/seotro95/seotro/releases/download/voice-studio-native-voxcpm-1.12.1-41214648685-1/'
OUTPUT_NAME = 'TAI_TOOL_DAY_DU_1.12.1.cmd'


def validate_manifest(value):
    if not isinstance(value, dict) or value.get('format') != 'voice-studio-full-zip-parts-v1':
        raise ValueError('Expected a full-ZIP release-parts manifest')
    name, size, digest = (value.get(k) for k in ('archive', 'archive_size', 'archive_sha256'))
    if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,140}\.zip', name)
            or re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', name)
            or type(size) is not int or not 0 < size <= 12 * 1024**3
            or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
        raise ValueError('Invalid archive filename, size or SHA256')
    parts = value.get('parts')
    if not isinstance(parts, list) or not 1 <= len(parts) <= 8:
        raise ValueError('A download needs between one and eight ordered parts')
    normalized = []
    for index, part in enumerate(parts, 1):
        if (not isinstance(part, dict) or part.get('name') != name + f'.part{index:03d}'
                or type(part.get('size')) is not int or not 0 < part['size'] < 2 * 1024**3
                or not isinstance(part.get('sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', part['sha256'])):
            raise ValueError('Invalid or unordered release part')
        normalized.append({k: part[k] for k in ('name', 'size', 'sha256')})
    if sum(p['size'] for p in normalized) != size:
        raise ValueError('Part sizes do not add up to the full ZIP')
    return {'archive': name, 'archive_size': size, 'archive_sha256': digest, 'parts': normalized}


def validate_base(value):
    if (not isinstance(value, str) or not re.fullmatch(
            r'https://github\.com/seotro95/seotro/releases/download/[A-Za-z0-9][A-Za-z0-9_.-]{0,160}/', value)):
        raise ValueError('Use an HTTPS release URL in seotro95/seotro, without query or fragment')
    return value


_TEMPLATE = r'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem This is a downloader. The complete application is downloaded afterward.
rem Only fixed release data is downloaded; downloaded scripts are not executed.
set "VS_EXIT=1"
set "VS_PUSHED="
pushd "%~dp0"
if errorlevel 1 goto failed
set "VS_PUSHED=1"
set "VS_ARCHIVE=@ARCHIVE@"
set "VS_FULL_SIZE=@FULL_SIZE@"
set "VS_FULL_SHA=@FULL_SHA@"
set "VS_BASE=@BASE@"
set "VS_FINAL=%CD%\%VS_ARCHIVE%"
set "VS_CACHE=%CD%\_Voice-Studio-Download-@CACHE@"
set "VS_STAGING=%VS_CACHE%\complete.zip.assembling"
set "VS_OWNER=voice-studio-download-v1 @FULL_SHA@"
where powershell.exe >nul 2>&1
if errorlevel 1 goto missing_powershell
echo VOICE STUDIO - TAI GOI DAY DU THANH MOT TEP ZIP
echo Day la tep tai tu dong, khong chua san toan bo tool.
echo Can Internet va khoang 20 GB dung luong trong de tai, ghep va giai nen.
echo Co the chay lai neu mat mang; cac phan da xac minh duoc dung lai.
echo.
set "VS_CHECK=%VS_FINAL%"
set "VS_EXPECT_SIZE=%VS_FULL_SIZE%"
set "VS_EXPECT_SHA=%VS_FULL_SHA%"
if not exist "%VS_FINAL%" goto prepare_cache
call :verify
if errorlevel 1 goto existing_zip_invalid
goto success

:prepare_cache
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';try{$p=$env:VS_CACHE;$m=Join-Path $p 'OWNER.txt';if(Test-Path -LiteralPath $p){$d=Get-Item -LiteralPath $p;if(-not $d.PSIsContainer -or ($d.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Cache path is not a regular directory'};if(-not(Test-Path -LiteralPath $m -PathType Leaf)){throw 'Existing cache has no ownership marker'};$f=Get-Item -LiteralPath $m;if(($f.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $f.Length -gt 256 -or [IO.File]::ReadAllText($m).Trim() -cne $env:VS_OWNER){throw 'Existing cache belongs to different data'}}else{$null=[IO.Directory]::CreateDirectory($p);[IO.File]::WriteAllText($m,$env:VS_OWNER+[Environment]::NewLine,[Text.Encoding]::ASCII)};exit 0}catch{Write-Host $_.Exception.Message;exit 1}"
if errorlevel 1 goto failed
set "VS_CURL="
where curl.exe >nul 2>&1
if not errorlevel 1 set "VS_CURL=1"
@PART_CALLS@
rem Rebuild only our staging file, never an existing user ZIP.
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';try{$p=$env:VS_STAGING;if(Test-Path -LiteralPath $p){$f=Get-Item -LiteralPath $p;if($f.PSIsContainer -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unsafe staging path'};Remove-Item -LiteralPath $p};exit 0}catch{Write-Host $_.Exception.Message;exit 1}"
if errorlevel 1 goto failed
echo Dang ghep mot tep ZIP day du...
copy /b @COPY_SOURCES@ "%VS_STAGING%" >nul
if errorlevel 1 goto failed
set "VS_CHECK=%VS_STAGING%"
set "VS_EXPECT_SIZE=%VS_FULL_SIZE%"
set "VS_EXPECT_SHA=%VS_FULL_SHA%"
call :verify
if errorlevel 1 goto full_hash_failed
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';try{[IO.File]::Move($env:VS_STAGING,$env:VS_FINAL);exit 0}catch{Write-Host $_.Exception.Message;exit 1}"
if errorlevel 1 goto failed

:success
set "VS_EXIT=0"
echo.
echo DA TAO VA KIEM TRA SHA256 MOT TEP ZIP DAY DU:
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Write-Host $env:VS_FINAL"
echo Giai nen toan bo ZIP vao thu muc moi. Sau do mo MO_TOOL.bat.
echo Khong can tai thu cong cac tep part hoac tep ghep nao khac.
goto finish

:existing_zip_invalid
echo ZIP cung ten da ton tai nhung khong khop. Tep cu duoc giu nguyen.
echo Hay dung mot thu muc moi cho tep tai nay.
goto failed
:full_hash_failed
echo Kich thuoc hoac SHA256 ZIP ghep khong khop. Khong su dung tep do.
goto failed
:missing_powershell
echo Can Windows PowerShell de kiem tra SHA256. Chua tai hoac chay tool.
goto failed
:failed
echo.
echo Chua hoan tat. Cac tep cu va cac phan da xac minh duoc giu nguyen.
echo Kiem tra ket noi va dung luong, roi chay lai tep tai nay.
:finish
if not defined VOICE_DOWNLOAD_NO_PAUSE pause
if defined VS_PUSHED popd
exit /b %VS_EXIT%

:verify
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';$s=$null;$h=$null;try{$p=$env:VS_CHECK;if(-not(Test-Path -LiteralPath $p -PathType Leaf)){exit 2};$f=Get-Item -LiteralPath $p;if(($f.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $f.Length -ne [long]$env:VS_EXPECT_SIZE){exit 1};$s=[IO.File]::OpenRead($p);$h=[Security.Cryptography.SHA256]::Create();$digest=([BitConverter]::ToString($h.ComputeHash($s))).Replace('-','').ToLowerInvariant();if($digest -cne $env:VS_EXPECT_SHA){exit 1};exit 0}catch{Write-Host $_.Exception.Message;exit 1}finally{if($null -ne $s){$s.Dispose()};if($null -ne $h){$h.Dispose()}}"
exit /b %ERRORLEVEL%

:part
set "VS_PART=%~1"
set "VS_EXPECT_SIZE=%~2"
set "VS_EXPECT_SHA=%~3"
set "VS_SLOT=%~4"
set "VS_NEAR=%CD%\%VS_PART%"
set "VS_FILE=%VS_CACHE%\%VS_PART%"
set "VS_PARTIAL=%VS_FILE%.partial"
set "VS_URL=%VS_BASE%%VS_PART%"
set "VS_CHECK=%VS_NEAR%"
call :verify
if not errorlevel 1 goto part_near
if not exist "%VS_FILE%" goto part_partial
set "VS_CHECK=%VS_FILE%"
call :verify
if errorlevel 1 goto part_existing_invalid
goto part_complete
:part_partial
set "VS_CHECK=%VS_PARTIAL%"
call :verify
if not errorlevel 1 goto part_move
rem This partial file is in our owner-marked cache. Reject redirects/symlinks.
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';try{$p=$env:VS_PARTIAL;if(Test-Path -LiteralPath $p){$f=Get-Item -LiteralPath $p;if($f.PSIsContainer -or ($f.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unsafe partial download path'};if($f.Length -ge [long]$env:VS_EXPECT_SIZE){Remove-Item -LiteralPath $p}};exit 0}catch{Write-Host $_.Exception.Message;exit 1}"
if errorlevel 1 exit /b 1
echo Dang tai va kiem tra %VS_PART% ...
if not defined VS_CURL goto part_webclient
set "VS_RESTARTED="
:part_curl
curl.exe --fail --location --show-error --progress-bar --proto "=https" --proto-redir "=https" --connect-timeout 30 --retry 2 --retry-delay 2 --continue-at - --output "%VS_PARTIAL%" "%VS_URL%"
set "VS_CURL_ERROR=%ERRORLEVEL%"
if "%VS_CURL_ERROR%"=="0" goto part_downloaded
if defined VS_RESTARTED goto part_network_failed
if "%VS_CURL_ERROR%"=="33" goto part_restart
if "%VS_CURL_ERROR%"=="36" goto part_restart
goto part_network_failed
:part_restart
set "VS_RESTARTED=1"
echo May chu khong cho tiep tuc phan dang do; tai lai rieng phan nay.
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';try{if(Test-Path -LiteralPath $env:VS_PARTIAL){Remove-Item -LiteralPath $env:VS_PARTIAL};exit 0}catch{Write-Host $_.Exception.Message;exit 1}"
if errorlevel 1 exit /b 1
goto part_curl
:part_webclient
echo Khong co curl.exe; PowerShell se tai lai phan dang do. Cac phan da xac minh van duoc dung lai.
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';$w=$null;try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;$w=New-Object Net.WebClient;$w.DownloadFile($env:VS_URL,$env:VS_PARTIAL);exit 0}catch{Write-Host $_.Exception.Message;exit 1}finally{if($null -ne $w){$w.Dispose()}}"
if errorlevel 1 goto part_network_failed
:part_downloaded
set "VS_CHECK=%VS_PARTIAL%"
call :verify
if errorlevel 1 goto part_download_invalid
:part_move
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$ErrorActionPreference='Stop';try{[IO.File]::Move($env:VS_PARTIAL,$env:VS_FILE);exit 0}catch{Write-Host $_.Exception.Message;exit 1}"
if errorlevel 1 exit /b 1
:part_complete
set "VS_SOURCE_%VS_SLOT%=%VS_FILE%"
echo Da xac minh %VS_PART%.
exit /b 0
:part_near
set "VS_SOURCE_%VS_SLOT%=%VS_NEAR%"
echo Dung lai phan da co va dung SHA256: %VS_PART%.
exit /b 0
:part_existing_invalid
echo Phan trong cache khong khop. Giu nguyen tep va dung thu muc tai moi.
exit /b 1
:part_download_invalid
echo Phan vua tai chua du hoac sai SHA256. Chay lai de tai lai rieng phan nay.
exit /b 1
:part_network_failed
echo Tai bi gian doan. Chay lai de tiep tuc; khong can tai lai cac phan da xac minh.
exit /b 1
'''


def make_script(manifest, base_url=DEFAULT_BASE):
    data, base_url = validate_manifest(manifest), validate_base(base_url)
    calls = []
    for index, part in enumerate(data['parts'], 1):
        calls.append(f'call :part "{part["name"]}" "{part["size"]}" "{part["sha256"]}" "{index:03d}"\nif errorlevel 1 goto failed')
    substitutions = {
        '@ARCHIVE@': data['archive'], '@FULL_SIZE@': str(data['archive_size']),
        '@FULL_SHA@': data['archive_sha256'], '@BASE@': base_url,
        '@CACHE@': data['archive_sha256'][:12], '@PART_CALLS@': '\n'.join(calls),
        '@COPY_SOURCES@': '+'.join(f'"%VS_SOURCE_{index:03d}%"' for index in range(1, len(data['parts']) + 1)),
    }
    script = _TEMPLATE
    for token, value in substitutions.items():
        script = script.replace(token, value)
    script.encode('ascii')
    if any(len(line) >= 8000 for line in script.splitlines()):
        raise ValueError('A generated command exceeds the Windows command-line limit')
    return script.replace('\r\n', '\n').replace('\n', '\r\n').encode('ascii')


def build(manifest, output, base_url=DEFAULT_BASE):
    manifest, output = Path(manifest), Path(output)
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 65536:
        raise ValueError('Use a regular, bounded JSON manifest')
    if output.suffix.lower() != '.cmd' or output.exists() or output.is_symlink():
        raise FileExistsError('Choose a new CMD output path; existing files are preserved')
    payload = make_script(json.loads(manifest.read_text(encoding='utf-8')), base_url)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(payload)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-url', default=DEFAULT_BASE)
    args = parser.parse_args(argv)
    print(build(args.manifest, args.output, args.base_url))


if __name__ == '__main__': main()
