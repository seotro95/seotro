"""Small, local Hmong reader with independent male/female references."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

import builtin_references
import cloning_engine
import voice_jobs
from hardware import hardware_info
from longform import MAX_CHARACTERS, STYLES

BASE = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app):
    yield
    await voice_jobs.shutdown()


app = FastAPI(title='Hmong Nhanh', version='0.5.0', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


class ReadingOptions(BaseModel):
    voice: Literal['hmong-white-female', 'hmong-white-male']
    speed: float = Field(default=1, ge=0.5, le=2, allow_inf_nan=False)
    quality: Literal['draft', 'fast', 'balanced', 'quality'] = 'fast'
    style: Literal['natural', 'storytelling', 'film_review', 'news', 'advertising', 'relaxing'] = 'natural'


class Speech(ReadingOptions):
    text: str = Field(min_length=1, max_length=MAX_CHARACTERS)


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
    items = []
    for gender, name in [('female', 'Nữ'), ('male', 'Nam')]:
        ident = 'hmong-white-' + gender
        try:
            ref = builtin_references.settings(ident)
            reference_ready = bool(ref.get('sample') and ref['text'].strip())
            reason = '' if reference_ready else 'Lưu lời khớp đoạn mẫu 3–8 giây cho giọng này.'
        except HTTPException as exc:
            ref = {'text': '', 'start': 0, 'end': 8, 'duration': 0}
            reference_ready = False
            reason = str(exc.detail)
        if not engine['ready']:
            reason = engine['reason']
        items.append({'id': ident, 'name': name, 'gender': gender,
                      'reference': f'/static/voices/{ident}.mp3',
                      'reference_settings': {k: v for k, v in ref.items() if k != 'sample'},
                      'reference_ready': reference_ready,
                      'generation_configured': engine['ready'] and reference_ready,
                      'reason': reason})
    return {'voices': items}


@app.put('/api/voices/{ident}/reference')
def save_reference(ident: str, payload: builtin_references.ReferenceSettings):
    builtin_references.save(ident, payload)
    return {'voice': next(item for item in voices()['voices'] if item['id'] == ident)}


def selected_reference(payload):
    if not payload.text.strip():
        raise HTTPException(422, 'Nhập văn bản cần đọc trước.')
    state = status()
    if not state['engine']['ready']:
        raise HTTPException(503, state['engine']['reason'])
    return builtin_references.selected(payload.voice)


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
    sample, transcript = await run_in_threadpool(selected_reference, payload)
    return await synthesize_reference(payload, sample, transcript)


def public_job(value):
    for part in value.get('parts', []):
        part['url'] = f"/api/speech/jobs/{value['id']}/parts/{part['number']}"
    return value


@app.post('/api/speech/jobs', status_code=202)
async def create_job(payload: Speech):
    sample, transcript = await run_in_threadpool(selected_reference, payload)
    # Freeze the chosen pair now. Saving a new reference cannot change a running job.
    data = payload.model_dump()
    data['_reference'] = {'path': str(sample.resolve()), 'text': transcript}
    return public_job(voice_jobs.create(data))


@app.post('/api/benchmark', status_code=202)
async def benchmark(payload: ReadingOptions):
    speech = Speech(text='Nyob zoo, hnub no koj nyob li cas?', **payload.model_dump())
    sample, transcript = await run_in_threadpool(selected_reference, speech)
    data = speech.model_dump()
    data.update(benchmark=True, _reference={'path': str(sample.resolve()), 'text': transcript})
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
