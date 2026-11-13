"""Verify transferred synthetic narration bytes and attach them to a draft release."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import base64, hashlib, json, os, subprocess, time, urllib.request, zipfile

REPO='seotro95/seotro';TAG='alula-095-20m42s';RELEASE_ID=444592871
ROOT=Path('episodes/alula-095')
assert os.environ.get('GITHUB_REPOSITORY')==REPO
manifest=json.loads((ROOT/'audio-transfer.json').read_text())
qa=json.loads((ROOT/'VOICE_QA.json').read_text())
assert manifest['repository']==REPO and len(manifest['parts'])==27
assert manifest['description']=='17 newly generated AlUla narration MP3 files; no raw speaker reference recordings'
assert len(qa['voices'])==17 and all(x['decoded_seconds']==1242 for x in qa['voices'])

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1048576):digest.update(block)
    return digest.hexdigest()

def gh(*args):
    return subprocess.run(['gh',*map(str,args)],check=True,text=True,capture_output=True).stdout

partdir=Path('verified-audio-parts');partdir.mkdir(exist_ok=True)
def download(part):
    assert len(part['blob_sha'])==40 and all(x in '0123456789abcdef' for x in part['blob_sha'])
    path=partdir/f"{part['index']:03d}.part"
    request=urllib.request.Request(f"https://api.github.com/repos/{REPO}/git/blobs/{part['blob_sha']}",headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github.raw+json','X-GitHub-Api-Version':'2022-11-28'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request,timeout=180) as response:data=response.read(part['bytes']*2+4096)
            if len(data)!=part['bytes'] and data.lstrip().startswith(b'{'):
                body=json.loads(data);data=base64.b64decode(body['content'])
            assert len(data)==part['bytes']
            assert hashlib.sha256(data).hexdigest()==part['sha256']
            path.write_bytes(data)
            return path
        except Exception:
            if attempt==2:raise
            time.sleep(3*(attempt+1))

with ThreadPoolExecutor(max_workers=4) as pool:parts=list(pool.map(download,manifest['parts']))
archive=Path(manifest['file'])
with archive.open('wb') as target:
    for path in parts:
        with path.open('rb') as source:
            while block:=source.read(1048576):target.write(block)
assert archive.stat().st_size==manifest['bytes'] and sha(archive)==manifest['sha256']

expected={x['file']:x['mp3_sha256'] for x in qa['voices']}
voices=Path('verified-voices');voices.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())==set(expected)|{'SHA256SUMS.txt'}
    assert z.testzip() is None
    for name,digest in expected.items():
        assert '/' not in name and '\\' not in name and name.endswith('.mp3')
        content=z.read(name);assert hashlib.sha256(content).hexdigest()==digest
        (voices/name).write_bytes(content)
print('Verified all 27 transfer parts, full ZIP, and 17 exact MP3 hashes.',flush=True)

gh('release','upload',TAG,archive,*sorted(voices.glob('*.mp3')),'--clobber')
release=json.loads(gh('api',f'repos/{REPO}/releases/{RELEASE_ID}'))
assets={x['name']:x for x in release['assets']}
for row in qa['voices']:
    asset=assets[row['file']]
    assert asset['size']==row['bytes']
    assert asset.get('digest')=='sha256:'+row['mp3_sha256']
assert assets[archive.name]['digest']=='sha256:'+manifest['sha256']

status=json.loads((ROOT/'DELIVERY_MANIFEST.json').read_text())
status.update(status='uploaded_to_github_draft_release',github_audio_upload_status='complete',github_release_id=RELEASE_ID,github_release_url=release['html_url'])
(ROOT/'DELIVERY_MANIFEST.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
upload_qa={'status':'all_17_uploaded_and_server_sha256_verified','repository':REPO,'release_id':RELEASE_ID,'release_url':release['html_url'],'workflow_run_id':os.environ['GITHUB_RUN_ID'],'target_seconds':1242,'audio_count':17,'audio_zip_sha256':manifest['sha256'],'audio':[{'file':r['file'],'bytes':r['bytes'],'sha256':r['mp3_sha256'],'server_digest':assets[r['file']]['digest']} for r in qa['voices']]}
(ROOT/'GITHUB_UPLOAD_QA.json').write_text(json.dumps(upload_qa,ensure_ascii=False,indent=2)+'\n')

documents=[p for p in ROOT.rglob('*') if p.is_file() and p.name not in {'audio-transfer.json','finish_audio_delivery.py','SHA256SUMS.txt'}]
(ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in sorted(documents)))
with zipfile.ZipFile('ALULA_095_TAI_LIEU_20m42s.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(documents+[ROOT/'SHA256SUMS.txt']):z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile('ALULA_095_13_TXT_PROMPTS.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((ROOT/'prompts').glob('*.txt')):z.write(p,p.name)
gh('release','upload',TAG,'ALULA_095_TAI_LIEU_20m42s.zip','ALULA_095_13_TXT_PROMPTS.zip',ROOT/'VOICE_PROFILES_LOCKED.json',ROOT/'DOI_CHIEU_THOI_LUONG_17_VOICE.csv',ROOT/'KICH_BAN_ANH_20m42s.txt',ROOT/'KICH_BAN_VIET_20m42s.txt',ROOT/'GITHUB_UPLOAD_QA.json','--clobber')
gh('release','edit',TAG,'--draft=true','--title','AlUla 095 — 20:42 — 125 prompts và 17 voice','--notes-file',ROOT/'GITHUB_RELEASE_NOTES.md')
print('Saved all 17 verified voices and documents to the draft release:',release['html_url'],flush=True)
