"""Patch only program files in the exact original Thêm Giọng update archive."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import zipfile

BASE_SHA = '078c57e35b32125ad6973f6eeb891d330af72ade36198d6115b457e07f978a23'
BASE_BYTES = 1407359695
PREFIX = 'Melo-Viet-Cai-Rieng/'
SOURCE = Path(__file__).resolve().parents[1]/'melo-viet-local'
PATCHES = ["timing.py","documents.py","speaking.py","app.py","audio_exports.py","setup.sh","app.js","index.html","tests/browser.cjs","tests/test_studio.py","tests/test_timing.py","HUONG_DAN.txt"]


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):value.update(block)
    return value.hexdigest()


def checked_archive(path, expected=BASE_SHA, size=BASE_BYTES):
    if path.stat().st_size != size or digest(path) != expected:
        raise ValueError('Original ZIP SHA-256/size mismatch')
    return zipfile.ZipFile(path)


def member_path(root, name):
    parts=PurePosixPath(name.replace('\\','/')).parts
    if not parts or '..' in parts or name.startswith('/') or ':' in parts[0]:
        raise ValueError('Invalid ZIP path')
    path=root.joinpath(*parts)
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def prepare(base, work):
    root=work/'Melo-Viet-Cai-Rieng'
    work.mkdir(parents=True,exist_ok=False)
    with checked_archive(base) as original:
        for entry in original.infolist():
            if not entry.filename.startswith(PREFIX):
                raise ValueError('Unexpected original package root')
            if entry.is_dir():
                member_path(work,entry.filename).mkdir(parents=True,exist_ok=True)
                continue
            target=member_path(work,entry.filename)
            with original.open(entry) as source,target.open('wb') as output:
                shutil.copyfileobj(source,output)
    for relative in PATCHES:
        target=root/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(SOURCE/relative,target)
    old=(root/'MANIFEST.sha256').read_text(encoding='utf-8')
    names={line.split('  ',1)[1] for line in old.splitlines() if line.strip()}
    names.update(PATCHES)
    (root/'MANIFEST.sha256').write_text(''.join(digest(root/name)+'  '+name+'\n' for name in sorted(names)),encoding='utf-8')
    print('PREPARED:',root,flush=True)


def seed(base, root):
    expected='b86fee41e348a32c0caa6f083b61057f5cd434c7f7c0e0f0bf6262fa3a80ab9b'
    prefix=PREFIX+'voice-pack/'
    count=0
    with checked_archive(base,expected,1581395769) as archive:
        for entry in archive.infolist():
            if not entry.filename.startswith(prefix+'models/') or entry.is_dir():
                continue
            target=member_path(root,entry.filename[len(prefix):])
            with archive.open(entry) as source,target.open('wb') as output:
                shutil.copyfileobj(source,output)
            count+=1
    if not count:
        raise ValueError('Base 1.2 package did not contain models')
    root.mkdir(parents=True,exist_ok=True)
    (root/'.melo-viet-local-owner').write_text('melo-viet-local-v1\n')
    print('SEEDED ORIGINAL 1.2 MODEL FILES:',count,flush=True)


def repack(base, work, qa_path):
    qa=json.loads(qa_path.read_text())
    if qa.get('status')!='passed' or qa.get('piper_presets')!=51 or qa.get('supertonic_languages')!=31:
        raise ValueError('Missing real native model timing proof')
    root=work/'Melo-Viet-Cai-Rieng'
    package=work/'Melo-Viet-Studio-1.3.1-Them-Giong-Windows.zip'
    root_manifest=(root/'MANIFEST.sha256').read_text().splitlines()
    for line in root_manifest:
        sha,name=line.split('  ',1)
        if digest(root/name)!=sha:
            raise ValueError('Program manifest mismatch: '+name)
    with checked_archive(base) as original,zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as output:
        records={entry.filename:entry for entry in original.infolist() if not entry.is_dir()}
        names=set(records)|{PREFIX+name for name in PATCHES}
        for name in sorted(names):
            relative=name[len(PREFIX):]
            info=copy.copy(records[name]) if name in records else zipfile.ZipInfo(name)
            info.compress_type=zipfile.ZIP_DEFLATED
            info._compresslevel=1
            with (root/relative).open('rb') as source,output.open(info,'w',force_zip64=True) as destination:
                shutil.copyfileobj(source,destination)
    with checked_archive(base) as original,zipfile.ZipFile(package) as result:
        before={e.filename:(e.CRC,e.file_size) for e in original.infolist() if e.filename.startswith(PREFIX+'voice-pack/') and not e.is_dir()}
        after={e.filename:(e.CRC,e.file_size) for e in result.infolist() if e.filename.startswith(PREFIX+'voice-pack/') and not e.is_dir()}
        if before!=after:
            raise ValueError('Original voice-pack contents changed')
        for name in ['CAP_NHAT.bat','MO_TOOL.bat','MO_OFFLINE.bat','bootstrap.ps1','start.sh']:
            if original.read(PREFIX+name)!=result.read(PREFIX+name):
                raise ValueError('Original launcher changed: '+name)
        if result.testzip() is not None:
            raise ValueError('Final ZIP CRC failure')
    if package.stat().st_size>BASE_BYTES+20*1024**2 or package.stat().st_size>=2*1024**3:
        raise ValueError('Unexpected package growth')
    proof={'version':'1.3.1','source_commit':os.environ.get('GITHUB_SHA'),
           'original_filename':'Melo-Viet-Studio-1.3.0-Them-Giong-Windows.zip',
           'original_zip_sha256':BASE_SHA,'original_zip_bytes':BASE_BYTES,
           'zip_bytes':package.stat().st_size,'zip_sha256':digest(package),
           'voice_pack_file_count':len(before),'original_voice_pack_unchanged':True,
           'original_launchers_unchanged':True,'native_timing_qa':qa}
    (work/'TXT-SRT-QA.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    Path(str(package)+'.sha256').write_text(proof['zip_sha256']+'  '+package.name+'\n')
    print('VERIFIED MELO UPDATE:',package,package.stat().st_size,proof['zip_sha256'],flush=True)
    print('UNCHANGED ORIGINAL VOICE-PACK FILES:',len(before),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['prepare','seed-base','repack'])
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--work',type=Path)
    p.add_argument('--root',type=Path)
    p.add_argument('--qa',type=Path)
    a=p.parse_args()
    if a.action=='prepare':prepare(a.base,a.work)
    elif a.action=='seed-base':seed(a.base,a.root)
    else:repack(a.base,a.work,a.qa)
