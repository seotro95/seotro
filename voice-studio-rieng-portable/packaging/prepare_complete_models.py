"""Prepare public optional models and isolated Windows CPU dependencies.

This is a normal model-pack build, not a relay: repository IDs, source assets,
runtime versions and output layout are fixed. Hugging Face main is resolved
once into immutable commits and blob hashes before downloading any weights.
No existing user installation, private recording or password is read.
"""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import zipfile

SOURCE = Path(__file__).resolve().parents[1]
BASE_SHA256 = '65446c1a1799699b3aadad616461e97cf66c049597c7ae9a5cbf3887f20312f6'
REPOSITORIES = {
    'qwen': ('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice', 'qwen-customvoice'),
    'qwen_clone': ('Qwen/Qwen3-TTS-12Hz-0.6B-Base', 'qwen-base'),
}
SPEAKERS = ('Ryan', 'Aiden', 'Ono_Anna', 'Sohee', 'Vivian', 'Serena', 'Uncle_Fu', 'Dylan', 'Eric')
OWNER = {'format': 'voice-studio-complete-model-pack-v1', 'version': '1.12.2'}
PUBLIC_REFERENCE = 'https://raw.githubusercontent.com/0xShug0/audio.cpp/2597b300f5961999387c84c65f2e8e79c088a571/assets/resources/b.wav'
REFERENCE_SHA256 = '32bf74dfb8342ccc8284f47a9e5fe1f41b458a983a00938ed170f76951ce638f'
QWEN_REQUIREMENTS = '''qwen-tts==0.1.1
transformers==4.57.3
accelerate==1.12.0
huggingface-hub==0.36.2
tokenizers==0.22.2
numpy==2.2.6
librosa==0.11.0
scipy==1.16.3
numba==0.61.2
llvmlite==0.44.0
soundfile==0.13.1
soxr==1.0.0
einops==0.8.1
onnxruntime==1.23.2
sox==1.5.0
gradio==5.49.1
'''


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def owned(root):
    root = Path(root)
    if root.is_symlink(): raise ValueError('Model-pack roots cannot be symlinks')
    root = root.resolve()
    marker = root / 'EXTRA-PACK-OWNER.json'
    if marker.is_symlink() or not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')) != OWNER:
        raise ValueError('Use the job-owned complete-model pack directory')
    return root


def native_preparer():
    spec = importlib.util.spec_from_file_location('voice_prepare_native', SOURCE / 'app/prepare_native.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _json_url(url, opener=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={'User-Agent': 'Voice-Studio-Complete-Models/1.12.2'})
    with opener(request, timeout=90) as response:
        raw = response.read(16 * 1024**2 + 1)
    if len(raw) > 16 * 1024**2: raise ValueError('Model metadata response exceeds its bound')
    return json.loads(raw)


def _model_file(name):
    if not isinstance(name, str): return False
    parts = PurePosixPath(name).parts
    if (not parts or '/'.join(parts) != name or '\\' in name or ':' in name
            or any(p in {'.', '..'} or p.endswith((' ', '.')) for p in parts)):
        return False
    if len(parts) > 1 and (parts[0] != 'speech_tokenizer' or len(parts) > 3): return False
    return (name in {'README.md', 'LICENSE', 'LICENSE.txt', 'LICENSE-APACHE-2.0.txt'}
            or PurePosixPath(name).suffix.lower() in {'.json', '.safetensors', '.txt', '.model', '.tiktoken'})


def resolve_qwen(engine, *, opener=urllib.request.urlopen):
    if engine not in REPOSITORIES: raise ValueError('Only the two official Qwen 0.6B repositories are supported')
    repository, folder = REPOSITORIES[engine]
    metadata = _json_url('https://huggingface.co/api/models/' + repository + '/revision/main?blobs=true', opener)
    revision = metadata.get('sha')
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Hugging Face did not resolve an immutable model revision')
    records, folded = [], set()
    for entry in metadata.get('siblings', []):
        name = entry.get('rfilename')
        if not _model_file(name): continue
        if name.casefold() in folded: raise ValueError('Duplicate or Windows-colliding model filename')
        folded.add(name.casefold())
        lfs = entry.get('lfs') or {}
        size = lfs.get('size', entry.get('size'))
        if type(size) is not int or not 0 < size <= 8 * 1024**3:
            raise ValueError('Missing or excessive immutable model file size: ' + name)
        digest = lfs.get('sha256')
        blob = entry.get('blobId')
        if digest is not None and not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Missing immutable LFS SHA256: ' + name)
        if digest is None and (not isinstance(blob, str) or not re.fullmatch('[0-9a-f]{40}', blob)):
            raise ValueError('Missing immutable Git blob identity: ' + name)
        records.append({'name': name, 'size': size, 'sha256': digest, 'git_blob_sha1': blob})
    names = {record['name'] for record in records}
    if not {'config.json', 'generation_config.json', 'tokenizer_config.json', 'model.safetensors',
            'speech_tokenizer/config.json', 'speech_tokenizer/preprocessor_config.json',
            'speech_tokenizer/model.safetensors'} <= names:
        raise ValueError('Qwen model metadata lacks main or speech-tokenizer configuration/weights')
    if 'tokenizer.json' not in names and not {'vocab.json', 'merges.txt'} <= names:
        raise ValueError('Qwen model metadata lacks the text tokenizer')
    if sum(record['size'] for record in records) > 8 * 1024**3:
        raise ValueError('The model exceeds the complete-pack bound')
    return {'schema': 1, 'backend': 'qwen-isolated', 'engine': engine,
            'repository': repository, 'revision': revision, 'model_dir': folder,
            'license': 'apache-2.0', 'files': sorted(records, key=lambda r:r['name'])}


def _download_record(url, target, record, *, opener=urllib.request.urlopen):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): raise FileExistsError('Download destination already exists: ' + target.name)
    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.part')
    expected_size = record['size']
    digest, git_digest, received = hashlib.sha256(), hashlib.sha1(), 0
    git_digest.update(f'blob {expected_size}\0'.encode('ascii'))
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'Voice-Studio-Complete-Models/1.12.2'})
        with opener(request, timeout=180) as incoming, temporary.open('xb') as output:
            for block in iter(lambda: incoming.read(8 * 1024**2), b''):
                received += len(block)
                if received > expected_size: raise ValueError('Model download exceeded its immutable size')
                digest.update(block); git_digest.update(block); output.write(block)
        if received != expected_size: raise ValueError('Incomplete model download')
        if record.get('sha256') and digest.hexdigest() != record['sha256']:
            raise ValueError('Immutable model LFS SHA256 mismatch')
        if not record.get('sha256') and git_digest.hexdigest() != record.get('git_blob_sha1'):
            raise ValueError('Immutable model Git blob SHA1 mismatch')
        temporary.rename(target)
        return {**record, 'sha256': digest.hexdigest()}
    finally:
        temporary.unlink(missing_ok=True)


def prepare(output):
    root = Path(output)
    if root.exists() or root.is_symlink(): raise FileExistsError('Use a new complete-model output directory')
    root.mkdir(parents=True)
    write_json(root / 'EXTRA-PACK-OWNER.json', OWNER)
    native = native_preparer()
    # Resolve and save the full immutable source plan BEFORE fetching weights.
    plans = {engine: resolve_qwen(engine) for engine in REPOSITORIES}
    plan = {**OWNER, 'qwen': plans,
            'omnivoice': {'size':native.MODEL_SIZE, 'sha256':native.MODEL_SHA256,
                         'url':native.MODEL_URL, 'revision':native.MODEL_REVISION},
            'asr': {'repository':native.ASR_REPOSITORY, 'revision':native.ASR_REVISION,
                    'files':native.ASR_FILES}}
    write_json(root / 'EXTRA-MODEL-PLAN.json', plan)
    data = root / 'app/.data'
    omni = native.prepare(data)
    asr = native.prepare_asr(data)
    qwen = {}
    for engine, record in plans.items():
        print('Downloading immutable ' + record['repository'] + '@' + record['revision'], flush=True)
        files = []
        for entry in record['files']:
            url = ('https://huggingface.co/' + record['repository'] + '/resolve/' + record['revision']
                   + '/' + urllib.parse.quote(entry['name'], safe='/') + '?download=true')
            files.append(_download_record(url, data / 'models' / record['model_dir'] / entry['name'], entry))
        marker = {**record, 'files':files, 'source_weights_verified':True,
                  'cpu_synthesis_tested':False, 'gpu_inference_tested':False,
                  'target_30x_guaranteed':False}
        write_json(data / 'models' / (engine + '.ready'), marker)
        qwen[engine] = marker
    write_json(root / 'EXTRA-MODEL-PINS.json', {**plan, 'qwen':qwen, 'omnivoice':omni, 'asr':asr,
                                               'private_recordings_or_passwords_included':False})
    return root


def _environment():
    result = dict(os.environ)
    for name in ('PYTHONHOME', 'PYTHONPATH'): result.pop(name, None)
    result.update(PYTHONNOUSERSITE='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  HF_HUB_DISABLE_XET='1', HF_HUB_DISABLE_TELEMETRY='1',
                  GRADIO_ANALYTICS_ENABLED='False', DO_NOT_TRACK='1')
    return result


def runtime(root, base_archive):
    root, base_archive = owned(root), Path(base_archive)
    if os.name != 'nt': raise ValueError('Windows CPU runtime assembly must run on Windows')
    if base_archive.is_symlink() or sha256(base_archive) != BASE_SHA256:
        raise ValueError('Pinned portable base archive SHA256 mismatch')
    target = root / 'runtime-qwen'
    if target.exists(): raise FileExistsError('The isolated Qwen runtime already exists')
    qa_root = root.parent/'qa-base-runtime'
    if qa_root.exists(): raise FileExistsError('The temporary main-runtime QA path already exists')
    qa_root.mkdir()
    write_json(qa_root/'EXTRA-PACK-OWNER.json',OWNER)
    from build_windows import safe_zip_path
    with zipfile.ZipFile(base_archive) as archive:
        for info in archive.infolist():
            parts = safe_zip_path(info)[1:]
            if info.is_dir() or not parts or parts[0] != 'runtime': continue
            relative = parts[1:]
            if not relative or any(p in {'.git', '.aws', '.agents', '.codex', '__pycache__'} for p in relative): continue
            if (relative[0] in {'Doc', 'Tools', 'Scripts', 'include', 'libs'}
                    or relative[0].startswith('python-') or relative[:2] == ('Lib','test')
                    or relative[:3] == ('Lib','idlelib','idle_test')): continue
            destinations = [(qa_root/'runtime').joinpath(*relative)]
            if relative[:2] != ('Lib','site-packages'): destinations.append(target.joinpath(*relative))
            for destination in destinations:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, destination.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024**2)
    python = target / 'python.exe'
    env = _environment()
    def run(args, timeout=3600):
        subprocess.run([str(python), '-s', '-X', 'utf8', *args], env=env, check=True, timeout=timeout)
    run(['-c', 'import sys;from pathlib import Path;assert sys.version_info[:3]==(3,12,10);assert Path(sys.prefix).resolve()==Path(sys.executable).resolve().parent'],30)
    run(['-m','ensurepip','--upgrade'],120)
    run(['-m','pip','--isolated','install','--disable-pip-version-check','--no-cache-dir','--no-compile',
         '--index-url','https://download.pytorch.org/whl/cpu','--report',str(root/'TORCH-INSTALL-REPORT.json'),
         'torch==2.8.0+cpu','torchaudio==2.8.0+cpu'])
    recipe = root / 'QWEN-RUNTIME-REQUIREMENTS.txt'; recipe.write_text(QWEN_REQUIREMENTS, encoding='utf-8')
    run(['-m','pip','--isolated','install','--disable-pip-version-check','--no-cache-dir','--no-compile','--prefer-binary',
         '--index-url','https://pypi.org/simple','--report',str(root/'QWEN-INSTALL-REPORT.json'),'-r',str(recipe)])
    run(['-m','pip','check'],120)
    # The original Nano/Turbo runtime already contains these exact four ASR
    # wheels. Test that unmodified runtime in a child; do not ship duplicates.
    subprocess.run([str(qa_root/'runtime/python.exe'),'-s','-X','utf8','-c',
        'import importlib.metadata as m; '
        'assert all(m.version(k)==v for k,v in '+repr({'faster-whisper':'1.2.1','ctranslate2':'4.8.3','av':'16.1.0','tokenizers':'0.23.3'})+'.items())'],
        env=env,check=True,timeout=60)
    packages = subprocess.check_output([str(python),'-s','-m','pip','list','--format=json'], env=env, text=True, encoding='utf-8')
    write_json(target/'VOICE-STUDIO-QWEN.json', {'schema':1,'backend':'qwen-isolated','torch':'2.8.0+cpu',
              'qwen_tts':'0.1.1','configured_device':'cpu','tested_device':None,'cpu_inference_tested':False,
              'precision':'fp32','base_archive_sha256':BASE_SHA256,
              'main_runtime_modified':False,'packages':json.loads(packages)})
    (root/'BUNDLED-QWEN-PACKAGES.txt').write_text(''.join(row['name']+'=='+row['version']+'\n'
        for row in sorted(json.loads(packages),key=lambda r:r['name'].casefold())),encoding='utf-8')
    pins=json.loads((root/'EXTRA-MODEL-PINS.json').read_text(encoding='utf-8'))
    pins['asr_runtime']={'uses_bundled_main_runtime':True,'base_archive_sha256':BASE_SHA256,
                         'packages':{'faster-whisper':'1.2.1','ctranslate2':'4.8.3','av':'16.1.0','tokenizers':'0.23.3'},
                         'heavy_imports_only_in_child':True,'duplicate_asr_runtime_bundled':False}
    write_json(root/'EXTRA-MODEL-PINS.json',pins)


def _valid_audio(samples, rate, destination):
    import numpy as np
    import soundfile as sf
    value = np.asarray(samples, dtype=np.float32)
    if (value.ndim != 1 or not 8000 <= rate <= 48000 or len(value) < rate * .08
            or not np.isfinite(value).all() or np.max(np.abs(value)) <= 0.00001):
        raise ValueError('Model did not generate valid non-silent PCM audio')
    sf.write(str(destination),value,rate,subtype='PCM_16')
    return {'valid_pcm_audio':True,'sample_rate':int(rate),'audio_seconds':len(value)/rate,'device':'cpu','precision':'fp32'}


def _marker_hashes(root):
    return {engine:sha256(root/'app/.data/models'/(engine+'.ready')) for engine in REPOSITORIES}


def smoke_asr(root, reference):
    root = owned(root)
    import importlib.metadata
    expected={'faster-whisper':'1.2.1','ctranslate2':'4.8.3','av':'16.1.0','tokenizers':'0.23.3'}
    if not all(importlib.metadata.version(k)==v for k,v in expected.items()): raise ValueError('Unexpected main ASR runtime versions')
    from faster_whisper import WhisperModel
    model = WhisperModel(str(root/'app/.data/models/native-asr'),device='cpu',compute_type='int8',cpu_threads=4,num_workers=1,local_files_only=True)
    segments,_ = model.transcribe(str(reference),language='en',beam_size=1,vad_filter=False,condition_on_previous_text=False)
    text = ' '.join(s.text.strip() for s in segments).strip()
    if not text or not any(c.isalnum() for c in text): raise ValueError('The real public reference was not transcribed')
    return {'valid_transcription':True,'device':'cpu','compute_type':'int8','faster_whisper':'1.2.1',
            'public_reference_sha256':REFERENCE_SHA256,'text':text,'private_reference_used':False}


def smoke(root, output):
    root = owned(root)
    qa_root=owned(root.parent/'qa-base-runtime')
    if os.name != 'nt' or Path(sys.executable).resolve() != (qa_root/'runtime/python.exe').resolve():
        raise ValueError('Use the exact pinned main Windows Python for adapter/ASR QA')
    validate_prepared_models(root)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    os.environ['VOICE_STUDIO_QWEN_PYTHON']=str(root/'runtime-qwen/python.exe')
    sys.path.insert(0,str(SOURCE/'app'))
    import qwen_backend
    import soundfile as sf
    if not qwen_backend.runtime_ready():raise ValueError('The actual adapter rejected the isolated Qwen runtime')
    if 'torch' in sys.modules:raise ValueError('Torch entered the main runtime before adapter QA')
    qa = root/'qa-public'; qa.mkdir()
    reference = qa/'public-reference.wav'
    with urllib.request.urlopen(PUBLIC_REFERENCE,timeout=90) as incoming, reference.open('xb') as destination:
        shutil.copyfileobj(incoming,destination)
    if sha256(reference) != REFERENCE_SHA256: raise ValueError('Public reference SHA256 mismatch')
    requests = []
    for speaker in SPEAKERS:
        language,text = (('ja','はい。') if speaker=='Ono_Anna' else ('ko','안녕.') if speaker=='Sohee'
                         else ('en-US','Hello.') if speaker in {'Ryan','Aiden'} else ('zh','你好。'))
        started = time.perf_counter()
        synth=qwen_backend.create_synthesizer(root/'app/.data',engine='qwen',language=language,speaker=speaker,
                                              threads=4,quality='fast',device='cpu')
        destination=qa/(speaker+'.wav');synth(text,destination)
        samples,rate=sf.read(str(destination),dtype='float32')
        requests.append({'speaker':speaker,'language':language,'seconds':time.perf_counter()-started,
                         **_valid_audio(samples,rate,destination),'execution':qwen_backend.execution_info()})
        print('Actual CPU PCM: '+speaker,flush=True)
    synth=qwen_backend.create_synthesizer(root/'app/.data',engine='qwen_clone',language='en-US',
        reference_audio=reference,reference_text='',threads=4,quality='fast',device='cpu')
    destination=qa/'base-clone.wav';synth('Hello.',destination)
    samples,rate=sf.read(str(destination),dtype='float32')
    base = {**_valid_audio(samples,rate,destination),'x_vector_only_mode':True,
            'execution':qwen_backend.execution_info(),
            'public_reference_sha256':REFERENCE_SHA256,'private_reference_used':False}
    qwen_backend.close_backends()
    if any(name in sys.modules for name in ('torch','transformers','qwen_tts')):
        raise ValueError('A heavy Qwen module escaped its isolated child')
    result = subprocess.run([sys.executable,'-s','-X','utf8',str(Path(__file__).resolve()),'smoke-asr',
                             '--root',str(root),'--reference',str(reference)],env=_environment(),
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',timeout=300)
    if result.returncode: raise RuntimeError('ASR CPU smoke failed: '+result.stderr[-5000:])
    asr = json.loads(result.stdout.strip())
    pins=json.loads((root/'EXTRA-MODEL-PINS.json').read_text(encoding='utf-8'))
    for engine in REPOSITORIES:
        path=root/'app/.data/models'/(engine+'.ready')
        marker=json.loads(path.read_text(encoding='utf-8'));marker['cpu_synthesis_tested']=True
        marker['cpu_synthesis_scope']='All nine official CustomVoice presets' if engine=='qwen' else 'Public-reference Base clone, x-vector-only'
        write_json(path,marker);pins['qwen'][engine]=marker
    write_json(root/'EXTRA-MODEL-PINS.json',pins)
    runtime_marker=root/'runtime-qwen/VOICE-STUDIO-QWEN.json'
    runtime_info=json.loads(runtime_marker.read_text(encoding='utf-8'))
    runtime_info.update(tested_device='cpu',cpu_inference_tested=True)
    write_json(runtime_marker,runtime_info)
    record = {'format':'voice-studio-extra-model-cpu-qa-v1','platform':'win32','version':'1.12.2',
              'qwen_customvoice':{'requests':requests,'tested_speakers':sorted(SPEAKERS)},'qwen_base':base,'asr':asr,
              'actual_application_adapter_tested':True,'main_runtime_heavy_qwen_imports':False,
              'qwen_model_markers_sha256':_marker_hashes(root),
              'runtime_manifest_sha256':sha256(root/'runtime-qwen/VOICE-STUDIO-QWEN.json'),
              'omnivoice_model_sha256':sha256(root/'app/.data/models/omnivoice/omnivoice-q8_0.gguf'),
              'omnivoice_inference_test':'not_run','gpu_inference_test':'not_run',
              'pronunciation_or_voice_identity_human_test':'not_run','full_hour_render_test':'not_run',
              'target_30x_guaranteed':False,'private_voice_library_decoded':False}
    validate_qa(root,record)
    write_json(output,record)
    write_json(root/'EXTRA-MODEL-CPU-QA.json',record)
    shutil.rmtree(qa)
    # The workflow removes qa_root after this interpreter exits; Windows keeps
    # its Python executable/DLLs open while this process is alive.
    return record


def validate_qa(root, report):
    if (report.get('format')!='voice-studio-extra-model-cpu-qa-v1' or report.get('platform')!='win32'
            or report.get('qwen_model_markers_sha256')!=_marker_hashes(root)
            or report.get('runtime_manifest_sha256')!=sha256(root/'runtime-qwen/VOICE-STUDIO-QWEN.json')
            or report.get('actual_application_adapter_tested') is not True
            or report.get('main_runtime_heavy_qwen_imports') is not False
            or report.get('gpu_inference_test')!='not_run' or report.get('target_30x_guaranteed') is not False
            or report.get('private_voice_library_decoded') is not False):
        raise ValueError('Windows CPU QA does not identify these exact prepared models/runtime')
    rows=report.get('qwen_customvoice',{}).get('requests',[])
    if (len(rows)!=9 or {r.get('speaker') for r in rows}!=set(SPEAKERS)
            or not all(r.get('valid_pcm_audio') is True and r.get('device')=='cpu' for r in rows)
            or report.get('qwen_base',{}).get('valid_pcm_audio') is not True
            or report.get('qwen_base',{}).get('device')!='cpu'
            or report.get('qwen_base',{}).get('public_reference_sha256')!=REFERENCE_SHA256
            or report.get('asr',{}).get('valid_transcription') is not True
            or report.get('asr',{}).get('device')!='cpu'
            or report.get('asr',{}).get('public_reference_sha256')!=REFERENCE_SHA256):
        raise ValueError('All nine Qwen voices, Base cloning and ASR must pass actual CPU checks')
    native=native_preparer()
    if report.get('omnivoice_model_sha256')!=native.MODEL_SHA256:
        raise ValueError('OmniVoice model differs from the pinned verified model')


def validate_prepared_models(root):
    data=root/'app/.data'
    native=native_preparer()
    native.verify_model(data/'models/omnivoice'/native.MODEL_FILENAME)
    for entry in native.ASR_FILES:
        if not native._verify_asr_file(data/'models/native-asr'/entry['name'],entry):
            raise ValueError('Prepared ASR file changed after its source verification')
    for engine,(repository,folder) in REPOSITORIES.items():
        marker=json.loads((data/'models'/(engine+'.ready')).read_text(encoding='utf-8'))
        if (marker.get('schema')!=1 or marker.get('backend')!='qwen-isolated' or marker.get('engine')!=engine
                or marker.get('repository')!=repository or marker.get('model_dir')!=folder
                or not re.fullmatch('[0-9a-f]{40}',str(marker.get('revision','')))):
            raise ValueError('Prepared Qwen marker does not identify the fixed model contract')
        seen=set()
        for entry in marker.get('files',[]):
            name=entry.get('name')
            if (not _model_file(name) or name.casefold() in seen or type(entry.get('size')) is not int
                    or not isinstance(entry.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',entry['sha256'])):
                raise ValueError('Invalid prepared Qwen file record')
            seen.add(name.casefold())
            path=data/'models'/folder/name
            if (path.is_symlink() or not path.is_file() or path.stat().st_size!=entry['size']
                    or sha256(path)!=entry['sha256']):raise ValueError('Prepared Qwen model changed after verification: '+name)
        if not {'config.json','generation_config.json','tokenizer_config.json','model.safetensors',
                'speech_tokenizer/config.json','speech_tokenizer/preprocessor_config.json','speech_tokenizer/model.safetensors'}<=seen:
            raise ValueError('Prepared Qwen model is incomplete')


def package(root, output, qa, release_parts=None):
    root,output = owned(root),Path(output)
    if output.exists() or Path(str(output)+'.sha256').exists(): raise FileExistsError('Choose a new output ZIP')
    record=json.loads(Path(qa).read_text(encoding='utf-8-sig'));validate_qa(root,record)
    validate_prepared_models(root)
    if Path(qa).resolve()!=(root/'EXTRA-MODEL-CPU-QA.json').resolve():
        shutil.copy2(qa,root/'EXTRA-MODEL-CPU-QA.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_name(output.name+'.'+uuid.uuid4().hex+'.assembling')
    digests={}
    try:
        with temporary.open('xb') as stream,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as target:
            for path in sorted(root.rglob('*')):
                if path.is_symlink(): raise ValueError('Model packs cannot contain symlinks')
                if not path.is_file(): continue
                parts=path.relative_to(root).parts
                if any(p in {'qa-public','__pycache__','.git','.aws','.agents','.codex'} for p in parts) or path.suffix.lower() in {'.pyc','.pyo'}:continue
                name='/'.join(parts)
                target.write(path,name);digests[name]=sha256(path)
            target.writestr('MANIFEST.sha256',''.join(value+'  '+name+'\n' for name,value in sorted(digests.items())))
        os.link(temporary,output)
        checksum=sha256(output)
        Path(str(output)+'.sha256').write_text(checksum+'  '+output.name+'\n',encoding='utf-8')
        if release_parts is not None:
            from build_full_update import split_release
            split_release(output,release_parts)
        return output
    finally:temporary.unlink(missing_ok=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    prep=commands.add_parser('prepare');prep.add_argument('--output',required=True,type=Path)
    run=commands.add_parser('runtime');run.add_argument('--root',required=True,type=Path);run.add_argument('--base-archive',required=True,type=Path)
    check=commands.add_parser('smoke');check.add_argument('--root',required=True,type=Path);check.add_argument('--output',required=True,type=Path)
    asr=commands.add_parser('smoke-asr');asr.add_argument('--root',required=True,type=Path);asr.add_argument('--reference',required=True,type=Path)
    pack=commands.add_parser('package');pack.add_argument('--root',required=True,type=Path);pack.add_argument('--output',required=True,type=Path);pack.add_argument('--qa',required=True,type=Path);pack.add_argument('--release-parts',type=Path)
    args=parser.parse_args(argv)
    if args.command=='prepare':print(prepare(args.output),flush=True)
    elif args.command=='runtime':runtime(args.root,args.base_archive)
    elif args.command=='smoke':smoke(args.root,args.output)
    elif args.command=='smoke-asr':print(json.dumps(smoke_asr(args.root,args.reference),ensure_ascii=False))
    else:print(package(args.root,args.output,args.qa,args.release_parts),flush=True)


if __name__=='__main__':main()
