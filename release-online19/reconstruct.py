"""Rebuild the exact verified private ZIP from immutable release bytes and an overlay.

No model code is executed and no runtime is installed. Only byte ranges from
SHA256-verified public release parts are copied. The final archive must match
the locally verified archive before any upload can start.
"""
import hashlib,json,os,subprocess,time,urllib.request,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('RUNNER_TEMP','/tmp'))/'online19-release-assets'
OUT.mkdir(exist_ok=True)

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def copy_range(source,target,source_offset,target_offset,count):
    source.seek(source_offset);target.seek(target_offset)
    while count:
        data=source.read(min(count,8*1024**2))
        if not data:raise ValueError('Truncated verified byte range')
        target.write(data);count-=len(data)

def main():
    recipe=json.loads((HERE/'recipe.json').read_text())
    assert sha(HERE/'overlay.bin')==recipe['overlay_sha256']
    assert sha(HERE/'small-assets.zip')==recipe['small_assets_sha256']
    final=OUT/recipe['final_name']
    with final.open('w+b') as target,(HERE/'overlay.bin').open('rb') as overlay:
        target.truncate(recipe['final_size'])
        for s in recipe['segments']:
            if s['source']=='overlay':copy_range(overlay,target,s['offset'],s['target'],s['length'])
        origin=0
        for part in recipe['base_parts']:
            begin,end=origin,origin+part['size'];origin=end
            needed=[]
            for s in recipe['segments']:
                if s['source']!='base':continue
                left=max(begin,s['offset']);right=min(end,s['offset']+s['length'])
                if right>left:needed.append((left-begin,s['target']+left-s['offset'],right-left))
            if not needed:continue
            download=OUT/'verified-source.part'
            url='https://github.com/seotro95/seotro/releases/download/'+recipe['source_release']+'/'+part['name']
            for attempt in range(3):
                try:
                    print('Downloading source part:',part['name'],flush=True)
                    with urllib.request.urlopen(url,timeout=120) as response,download.open('wb') as f:
                        count=0
                        while block:=response.read(8*1024**2):
                            count+=len(block)
                            if count>part['size']:raise ValueError('Source exceeds expected size')
                            f.write(block)
                    if download.stat().st_size!=part['size'] or sha(download)!=part['sha256']:raise ValueError('Source SHA256 mismatch')
                    break
                except Exception:
                    if attempt==2:raise
                    time.sleep(3)
            with download.open('rb') as stream:
                for so,to,count in needed:copy_range(stream,target,so,to,count)
            download.unlink()
            print('Verified/copied source part:',part['name'],flush=True)
    assert sha(final)==recipe['final_sha256'],'Reconstructed ZIP differs from reviewed ZIP'
    with zipfile.ZipFile(HERE/'small-assets.zip') as z:
        for i in z.infolist():
            if Path(i.filename).name!=i.filename or '\\' in i.filename:raise ValueError('Unsafe asset path')
            (OUT/i.filename).write_bytes(z.read(i))
    expected={p.name:{'size':p.stat().st_size,'sha256':sha(p)} for p in OUT.iterdir() if p.is_file()}
    assert expected == json.loads((HERE/'expected-assets.json').read_text()), 'Assets differ from reviewed manifest'
    print('Exact archive and all release assets verified:',recipe['final_sha256'],flush=True)

if __name__=='__main__':main()
