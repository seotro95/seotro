import concurrent.futures
import csv
import hashlib
import io
import json
import re
import subprocess
import urllib.request
import zipfile
from pathlib import Path

R = Path(__file__).parent
BASE = 'https://github.com/seotro95/seotro/releases/download/upano-moi-011-20m22s/'
FRAMES = 58656000

def get(name):
    with urllib.request.urlopen(BASE+name+'?v=43909217031',timeout=60) as response:
        assert response.status == 200
        return response.read()

manifest = json.loads(get('DOCUMENT_ASSET_MANIFEST.json'))
assert manifest['stage'] == 'all16voices_and_documents_published'
assets = {x['name']:x for x in manifest['assets']}

def verified_bytes(name):
    data = get(name)
    assert len(data) == assets[name]['bytes']
    assert hashlib.sha256(data).hexdigest() == assets[name]['sha256']
    return data

audio = json.loads(verified_bytes('AUDIO_MANIFEST.json'))
qa = json.loads(verified_bytes('VOICE_RELEASE_QA.json'))
profiles = json.loads(verified_bytes('VOICE_PROFILES_LOCKED.json'))
assert qa['status'] == 'passed' and qa['voices'] == 16 and qa['male_voices'] == 16
assert qa['all_decoded_frames_48000'] == FRAMES and qa['all_decoded_seconds'] == 1222
expected = {p['locale']:p for p in json.loads((R/'VOICE_PROFILES_LOCKED_BASELINE.json').read_text())['profiles']}
assert set(v['locale'] for v in audio['voices']) == set(expected)
for voice in audio['voices']:
    assert voice['voice_id'] == expected[voice['locale']]['voice_id'] and voice['gender'] == 'Male'
    assert voice['seconds'] == 1222 and voice['frames_at_48000'] == FRAMES
    assert assets[voice['filename']]['sha256'] == voice['sha256']

zipname = 'UPANO_MOI011_16_VOICES_20m22s.zip'
path = R/zipname
record = assets[zipname]
if not path.exists() or hashlib.file_digest(path.open('rb'),'sha256').hexdigest() != record['sha256']:
    partial = path.with_suffix('.partial')
    with urllib.request.urlopen(BASE+zipname+'?v='+record['sha256'],timeout=90) as response, partial.open('wb') as stream:
        assert response.status == 200
        while block := response.read(1024*1024):
            stream.write(block)
    assert partial.stat().st_size == record['bytes']
    assert hashlib.file_digest(partial.open('rb'),'sha256').hexdigest() == record['sha256']
    partial.replace(path)
print('PUBLIC_VOICE_ZIP_HASH_VERIFIED',record['sha256'],flush=True)

decoded = []
temporary = R/'public-verify-one-voice.mp3'
with zipfile.ZipFile(path) as archive:
    assert archive.testzip() is None
    names = [n for n in archive.namelist() if n.endswith('.mp3')]
    assert len(names) == 16
    for voice in audio['voices']:
        h = hashlib.sha256()
        with archive.open(voice['filename']) as source, temporary.open('wb') as dest:
            while block := source.read(1024*1024):
                h.update(block)
                dest.write(block)
        assert h.hexdigest() == voice['sha256']
        process = subprocess.Popen(['ffmpeg','-v','error','-nostdin','-i',str(temporary),
                                    '-ar','48000','-ac','1','-f','s16le','-'],
                                   stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        count = 0
        while block := process.stdout.read(1024*1024):
            count += len(block)
        error = process.stderr.read().decode('utf-8','replace')
        assert process.wait() == 0,error[-1000:]
        assert count == FRAMES*2,(voice['locale'],count)
        decoded.append(dict(locale=voice['locale'],voice_id=voice['voice_id'],frames=FRAMES,seconds=1222,sha256=voice['sha256']))
        print('PUBLIC_MP3_DECODED',voice['locale'],FRAMES,flush=True)
        temporary.unlink()

def check_link(voice):
    request = urllib.request.Request(voice['url'],method='HEAD')
    with urllib.request.urlopen(request,timeout=35) as response:
        assert response.status == 200
        length = response.headers.get('Content-Length')
        if length:
            assert int(length) == voice['bytes']
        return dict(locale=voice['locale'],http=200,url=voice['url'])

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    links = list(pool.map(check_link,audio['voices']))
document_name = 'UPANO_MOI011_TAI_LIEU_20m22s.zip'
docs = verified_bytes(document_name)
(R/document_name).write_bytes(docs)
with zipfile.ZipFile(io.BytesIO(docs)) as archive:
    assert archive.testzip() is None
    prompt_names = sorted(n for n in archive.namelist() if n.startswith('PROMPTS/') and n.endswith('.txt'))
    assert len(prompt_names) == 13
    ids = []
    for name in prompt_names:
        text = archive.read(name).decode('utf-8')
        prompts = [line for line in text.splitlines() if re.match(r'^\d{3}\. ',line)]
        assert len(prompts) == 10
        for prompt in prompts:
            assert prompt.endswith('Video không có âm thanh, không có lời nói.')
            assert 'No children, infants, adolescents, minors' in prompt
            ids.append(int(prompt[:3]))
    assert ids == list(range(1,131))
    timeline = list(csv.DictReader(io.StringIO(archive.read('TIMELINE_130_CANH.csv').decode('utf-8-sig'))))
    assert len(timeline) == 130 and sum(float(r['use_seconds']) for r in timeline) == 1222
    assert all(float(a['end']) == float(b['start']) for a,b in zip(timeline,timeline[1:]))
    assert json.loads(archive.read('DOCUMENT_QA.json'))['voices_generated']
    assert len(re.findall(r'^\d\. ',archive.read('5_TIEU_DE_VA_THUMBNAIL.txt').decode('utf-8'),re.M)) == 5
    for item in archive.infolist():
        if item.filename.endswith(('.txt','.md','.json','.csv','.srt')):
            assert '\ufffd' not in archive.read(item).decode('utf-8-sig')
    for item in archive.infolist():
        assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
        out = R/'verified-final-documents'/item.filename
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes(archive.read(item))
result = dict(status='passed',topic_id='MOI-011',voices=16,male_voices=16,seconds_each=1222,
              decoded_frames_48000_each=FRAMES,public_zip_crc='passed',public_zip_sha256=record['sha256'],
              documents_zip_sha256=assets[document_name]['sha256'],voices_decoded=decoded,individual_links=links,
              prompt_txt_files=13,unique_prompts=130,timeline_shots=130,timeline_seconds=1222,
              independent_native_listening_review=False)
(R/'PUBLIC_DELIVERY_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('UPANO_PUBLIC_DELIVERY_QA_PASSED',flush=True)
