$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip update failed' }
python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'dependency install failed' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'unit tests failed' }

# Download directly from upstream into the test user's local cache. FFmpeg
# binaries and model weights are NOT redistributed in the application ZIP.
@'
from autodoc import bootstrap
from autodoc.common import Context
old=bootstrap.binary
calls=[0]
def first_missing(name):
    calls[0]+=1
    if calls[0]==1:raise RuntimeError('force first-install test')
    return old(name)
bootstrap.binary=first_missing
bootstrap.ensure_ffmpeg(Context())
'@ | python -
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg first-install test failed' }

$argsBuild = @('--noconfirm','--clean','--onedir','--windowed','--name','AutoDocStudio',
 '--collect-all','ctranslate2','--collect-all','faster_whisper','--collect-all','onnxruntime',
 '--collect-all','tokenizers','--collect-all','av','--collect-all','huggingface_hub',
 '--copy-metadata','numpy','--copy-metadata','Pillow','--copy-metadata','onnxruntime',
 '--copy-metadata','tokenizers','--copy-metadata','huggingface-hub','--copy-metadata','faster-whisper',
 '--copy-metadata','ctranslate2','--copy-metadata','av','main.py')
python -m PyInstaller @argsBuild
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$exe = Join-Path $PSScriptRoot 'dist\AutoDocStudio\AutoDocStudio.exe'
$doctor = Join-Path $PSScriptRoot 'doctor-frozen.json'
$p=Start-Process -FilePath $exe -ArgumentList @('--doctor','--doctor-output',$doctor) -Wait -PassThru
if ($p.ExitCode -ne 0 -or -not (Test-Path $doctor)) { throw 'Frozen dependencies check failed' }
$d=Get-Content $doctor -Raw | ConvertFrom-Json
if ($d.status -ne 'ready') { throw 'Frozen doctor not ready' }
$p=Start-Process -FilePath $exe -ArgumentList '--gui-smoke' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Frozen Tkinter GUI failed' }
python windows_smoke.py $exe
if ($LASTEXITCODE -ne 0) {
 Get-Content "$env:LOCALAPPDATA\AutoDocStudio\application.log" -Tail 100 -ErrorAction SilentlyContinue
 throw 'Frozen full automatic edit test failed'
}
python package_release.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
