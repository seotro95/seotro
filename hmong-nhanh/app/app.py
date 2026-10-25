"""Small, local Hmong reader with independent male/female references."""
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
from typing import Literal
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

import builtin_references
import custom_references
import cloning_engine
import voice_jobs
from documents import parse_document
from hardware import hardware_info
from longform import MAX_CHARACTERS, STYLES

BASE = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app):
    yield
    await voice_jobs.shutdown()


app = FastAPI(title='Hmong Nhanh', version='0.6.0', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


class ReadingOptions(BaseModel):
    voice: str = Field(pattern=r'^(hmong-white-(female|male)|custom-[0-9a-f]{32})$')
    speed: float = Field(default=1, ge=0.5, le=2, allow_inf_nan=False)
    quality: Literal['draft', 'fast', 'balanced', 'quality'] = 'fast'
    style: Literal['natural', 'storytelling', 'film_review', 'news', 'advertising', 'relaxing'] = 'natural'
    timing: Literal['auto', 'natural'] = 'auto'


class Speech(ReadingOptions):
    text: str = Field(min_length=1, max_length=MAX_CHARACTERS)


class DocumentInput(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARACTERS)
    timing: Literal['auto', 'natural'] = 'auto'


def parsed_document(payload):
    try:
        return parse_document(payload.text, timing=payload.timing)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post('/api/documents/preview')
def preview_document(payload: DocumentInput):
    document = parsed_document(payload)
    return {**document, 'characters': len(document['text']), 'cue_count': len(document['cues']),
            'text': document['text'][:4000], 'cues': document['cues'][:10],
            'preview_truncated': len(document['text']) > 4000 or len(document['cues']) > 10}


@app.get('/')
def index():
    return FileResponse(BASE / 'static/index.html', headers={'Cache-Control': 'no-store'})


@app.get('/api/status')
def status():
    engine = cloning_engine.availability()
    return {'name': 'Hmong Nhanh', 'version': app.version, 'engine': engine,
            'hardware': hardware_info(), 'quality_modes': cloning_engine.QUALITY_STEPS,
            'styles': STYLES, 'max_characters': MAX_CHARACTERS, 'ready': engine['ready']}


@app.get('/api/voices')
def voices():
    engine = cloning_engine.availability()
    identifiers = list(builtin_references.VOICE_IDS) + custom_references.list_ids()
    return {'voices': [voice_details(ident, engine) for ident in identifiers]}


def reference_library(ident):
    return builtin_references if ident in builtin_references.VOICE_IDS else custom_references


def voice_name(ident):
    return {'hmong-white-female': 'Nữ', 'hmong-white-male': 'Nam'}.get(ident) or custom_references.name(ident)


def voice_details(ident, engine=None):
    engine = engine or cloning_engine.availability()
    name = voice_name(ident)
    try:
        ref = reference_library(ident).settings(ident)
        reference_ready = bool(ref.get('sample') and ref['text'].strip())
        reason = '' if reference_ready else 'Lưu lời khớp đoạn mẫu 3–8 giây cho giọng này.'
    except HTTPException as exc:
        ref = {'text': '', 'start': 0, 'end': 8, 'duration': 0}
        reference_ready = False
        reason = str(exc.detail)
    if not engine['ready']:
        reason = engine['reason']
    return {'id': ident, 'name': name,
            'gender': ident.removeprefix('hmong-white-') if ident in builtin_references.VOICE_IDS else 'custom',
            'reference': f'/api/voices/{ident}/source',
            'reference_settings': {k: v for k, v in ref.items() if k != 'sample'},
            'reference_ready': reference_ready,
            'generation_configured': engine['ready'] and reference_ready, 'reason': reason}


@app.post('/api/voices/upload', status_code=201)
async def upload_voice(request: Request):
    limit = custom_references.MAX_UPLOAD_BYTES
    declared = request.headers.get('content-length')
    if declared:
        try:
            if int(declared) > limit:
                raise HTTPException(413, 'Mẫu giọng tối đa 50 MB.')
        except ValueError:
            raise HTTPException(400, 'Kích thước tệp không hợp lệ.') from None
    name = unquote(request.headers.get('x-voice-name', 'Giọng của tôi'))
    filename = unquote(request.headers.get('x-file-name', 'sample.wav'))
    total = 0
    with tempfile.TemporaryDirectory(prefix='hmong-upload-') as folder:
        path = Path(folder) / 'upload.bin'
        with path.open('wb') as destination:
            async for chunk in request.stream():
                total += len(chunk)
                if total > limit:
                    raise HTTPException(413, 'Mẫu giọng tối đa 50 MB.')
                await run_in_threadpool(destination.write, chunk)
        ident = await run_in_threadpool(custom_references.register, path, name, filename)
    return {'voice': await run_in_threadpool(voice_details, ident)}


@app.get('/api/voices/{ident}/source')
def source_voice(ident: str):
    path = reference_library(ident).original(ident)
    return FileResponse(path, headers={'Cache-Control': 'no-store'})


@app.put('/api/voices/{ident}/reference')
def save_reference(ident: str, payload: builtin_references.ReferenceSettings):
    reference_library(ident).save(ident, payload)
    return {'voice': voice_details(ident)}


def selected_reference(payload):
    if not payload.text.strip():
        raise HTTPException(422, 'Nhập văn bản cần đọc trước.')
    state = status()
    if not state['engine']['ready']:
        raise HTTPException(503, state['engine']['reason'])
    return reference_library(payload.voice).selected(payload.voice)


async def synthesize_reference(payload, sample, transcript):
    try:
        audio = await run_in_threadpool(cloning_engine.synthesize, payload.text, payload.speed,
                                       sample, transcript, quality=payload.quality)
        return Response(audio, media_type='audio/wav', headers={'Cache-Control': 'no-store'})
    except cloning_engine.CloningError as exc:
        raise HTTPException(503, str(exc)) from None


@app.post('/api/speech')
async def speech(payload: Speech):
    if len(payload.text) > 2000 or payload.style != 'natural':
        raise HTTPException(422, 'Dùng /api/speech/jobs cho văn bản dài hoặc kiểu đọc tùy chọn.')
    document = await run_in_threadpool(parsed_document, payload)
    if document['timed']:
        raise HTTPException(422, 'Dùng /api/speech/jobs để căn âm thanh theo mốc phụ đề.')
    payload = payload.model_copy(update={'text': document['text']})
    sample, transcript = await run_in_threadpool(selected_reference, payload)
    return await synthesize_reference(payload, sample, transcript)


def public_job(value):
    for part in value.get('parts', []):
        part['url'] = f"/api/speech/jobs/{value['id']}/parts/{part['number']}"
    return value


@app.post('/api/speech/jobs', status_code=202)
async def create_job(payload: Speech):
    document = await run_in_threadpool(parsed_document, payload)
    sample, transcript = await run_in_threadpool(selected_reference, payload)
    # Freeze the chosen pair now. Saving a new reference cannot change a running job.
    data = payload.model_dump()
    data['_reference'] = {'path': str(sample.resolve()), 'text': transcript}
    data.update(voice_name=voice_name(payload.voice), source_format=document['format'],
                spoken_characters=len(document['text']), target_seconds=document['duration'] if document['timed'] else None)
    return public_job(voice_jobs.create(data))


@app.post('/api/benchmark', status_code=202)
async def benchmark(payload: ReadingOptions):
    speech = Speech(text='Nyob zoo, hnub no koj nyob li cas?', **payload.model_dump())
    sample, transcript = await run_in_threadpool(selected_reference, speech)
    data = speech.model_dump()
    data.update(benchmark=True, _reference={'path': str(sample.resolve()), 'text': transcript})
    data['voice_name'] = voice_name(payload.voice)
    return public_job(voice_jobs.create(data))


@app.get('/api/speech/jobs')
async def list_jobs():
    return {'jobs': [public_job(value) for value in voice_jobs.list_jobs()]}


@app.get('/api/speech/jobs/{ident}')
async def job_status(ident: str):
    return public_job(voice_jobs.view(voice_jobs.get(ident)))


@app.post('/api/speech/jobs/{ident}/stop')
async def stop_job(ident: str):
    return public_job(await voice_jobs.cancel(ident))


@app.post('/api/speech/jobs/{ident}/resume', status_code=202)
async def resume_job(ident: str):
    return public_job(voice_jobs.resume(ident))


@app.get('/api/speech/jobs/{ident}/parts/{number}')
async def job_part(ident: str, number: int):
    job = voice_jobs.get(ident)
    part = next((part for part in voice_jobs.view(job)['parts'] if part['number'] == number), None)
    if part is None:
        raise HTTPException(404, 'Phần âm thanh này chưa hoàn tất.')
    return FileResponse(job['folder'] / 'parts' / part['filename'], media_type='audio/wav',
                        filename=f"hmong-{ident[:8]}-{part['filename']}",
                        content_disposition_type='inline', headers={'Cache-Control': 'no-store'})


@app.get('/api/speech/jobs/{ident}/audio')
async def job_audio(ident: str):
    job = voice_jobs.get(ident)
    if job['status'] != 'completed':
        raise HTTPException(409, 'Bản đọc chưa hoàn tất.')
    parts = voice_jobs.view(job)['parts']
    if len(parts) != 1:
        raise HTTPException(422, 'Bản đọc dài có nhiều phần; chọn phần cần nghe hoặc tải.')
    return await job_part(ident, parts[0]['number'])
