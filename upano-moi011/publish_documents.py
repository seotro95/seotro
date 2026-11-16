from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

R = Path(__file__).parent
D = R / 'documents'
REPO = 'seotro95/seotro'
TAG = 'upano-moi-011-20m22s'

subprocess.run([sys.executable, str(R / 'build_documents.py')], check=True)
qa = json.loads((D / 'DOCUMENT_QA.json').read_text())
assert qa['status'] == 'passed' and qa['target_seconds'] == 1222
assert qa['unique_prompts'] == 130 and qa['prompt_txt_files'] == 13
en_path = next(Path('preflight/en-US').rglob('render_report.json'))
vi_path = next(Path('preflight/vi-VN').rglob('NAM_MINH_PREFLIGHT_QA.json'))
en = json.loads(en_path.read_text())
vi = json.loads(vi_path.read_text())
assert en['status'] == 'passed' and en['voice_id'] == 'en-US-AndrewNeural'
assert en['decoded_frames_48000'] == 1440000 and en['word_metadata_exact_script_match']
assert vi['status'] == 'passed' and vi['voice_id'] == 'vi-VN-NamMinhNeural'
assert vi['gender'] == 'Male' and vi['decoded_frames_48000'] == 480000 and vi['catalogue_verified']
rows = json.loads((R / 'voice/scripts/en-US.json').read_text())
request = json.loads(next(Path('preflight/en-US').rglob('group-001.request.json')).read_text())
body = ' '.join(r['voice'] for r in rows[:3])
signature = hashlib.sha256((body + '\0en-US-AndrewNeural\0+0%').encode()).hexdigest()
assert request['request_signature'] == signature
state = {'topic_id': 'MOI-011', 'documents_published': True, 'target_seconds': 1222,
         'english_preview_30s_verified': True, 'namminh_preview_10s_verified': True,
         'preflight_run_id': 43902964757, 'source_commit': os.environ['GITHUB_SHA']}
(D / 'DOCUMENT_DELIVERY_STATE.json').write_text(json.dumps(state, indent=2) + '\n')
exists = subprocess.run(['gh', 'release', 'view', TAG, '--repo', REPO], capture_output=True)
assert exists.returncode != 0, 'Existing release must be inspected before any replacement'
subprocess.run(['gh', 'release', 'create', TAG, '--repo', REPO, '--target', os.environ['GITHUB_SHA'],
                '--title', 'MỚI-011 Upano — Kịch bản và 130 prompt — 20:22',
                '--notes-file', str(D / 'README.md'), '--latest=false'], check=True)
names = ['KICH_BAN_EN_20m22s.txt', 'KICH_BAN_EN_CO_MOC.txt', 'en-US.srt', 'TIMELINE_130_CANH.csv',
         'HUONG_DAN_SU_DUNG.txt', '5_TIEU_DE_VA_THUMBNAIL.txt', 'NGUON_KIEM_CHUNG.md',
         'PHAN_TICH_VA_KE_HOACH_DUNG.md', 'VOICE_PROFILES_LOCKED_BASELINE.json', 'DOCUMENT_QA.json',
         'DOCUMENT_DELIVERY_STATE.json', 'OPENING_10_SHOTS_30s.json', 'PRODUCTION_STEPS_APPLIED.md', 'README.md']
assets = [R / 'UPANO_MOI011_TAI_LIEU_20m22s.zip'] + [D / n for n in names] + sorted((D / 'PROMPTS').glob('*.txt'))
assets.extend(Path('preflight/en-US').rglob('UPANO_MOI011_EN_PREVIEW_30s.mp3'))
assets.extend(Path('preflight/vi-VN').rglob('UPANO_MOI011_Viet_Nam_Nam_Minh_PREVIEW_10s.mp3'))
for path in assets:
    subprocess.run(['gh', 'release', 'upload', TAG, str(path), '--repo', REPO], check=True)
    print('DOCUMENT_PUBLISHED', path.name, flush=True)
manifest = {'topic_id': 'MOI-011', 'stage': 'documents_and_two_real_voice_previews_published',
            'assets': [{'name':p.name, 'bytes':p.stat().st_size,
                        'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in assets]}
path = D / 'DOCUMENT_ASSET_MANIFEST.json'
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
subprocess.run(['gh', 'release', 'upload', TAG, str(path), '--repo', REPO], check=True)
print('UPANO_DOCUMENTS_READY', flush=True)
