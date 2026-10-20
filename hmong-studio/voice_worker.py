"""Keep the local model warm in an isolated, cancellable JSON-lines worker.

Standard output and standard error belong to the parent-owned log file. Results
and measured progress use atomic per-job files, never the model's console logs.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from fastapi import HTTPException
from fastapi.responses import FileResponse


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True), encoding='utf-8')
    # Short-lived progress readers can overlap a replace on Windows.
    for attempt in range(4):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.01)


def _control(folder):
    path = folder / 'control.json'
    try:
        if path.stat().st_size > 4096:
            return None
        value = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(value, dict) or set(value) != {'revision', 'paused'}
                or isinstance(value['revision'], bool) or not isinstance(value['revision'], int)
                or not 0 <= value['revision'] <= 1000000000 or not isinstance(value['paused'], bool)):
            return None
        return value
    except (OSError, ValueError, TypeError):
        return None


def _metadata(path, value):
    try:
        atomic_json(path, value)
    except (OSError, TypeError, ValueError):
        # Metadata readers must not discard otherwise valid generated audio.
        pass


def _acknowledge(folder, control, state):
    key = (control['revision'], control['paused'])
    if state.get('key') != key:
        state.update(key=key, at_monotonic=time.monotonic())
    _metadata(folder / 'control-ack.json', {
        **control, 'at_monotonic': state['at_monotonic']})


def cooperative_checkpoint(folder, progress, state=None):
    """Pause only between model operations; a running CUDA kernel is untouched."""
    control = _control(folder)
    if control is None:
        return
    state = {} if state is None else state
    while control['paused']:
        _acknowledge(folder, control, state)
        _metadata(folder / 'progress.json', {
            **progress, 'phase': 'paused', 'active_workers': 0,
            'message': 'Đã tạm dừng ở ranh giới đoạn. Bấm Tiếp tục để tạo tiếp.'})
        # The parent can still cancel this owned process while its checkpoint
        # waits. A malformed/intermediate control file never resumes it.
        while True:
            time.sleep(.1)
            next_control = _control(folder)
            if next_control is not None:
                break
        control = next_control
    _acknowledge(folder, control, state)


def runtime_snapshot(app):
    try:
        engine = getattr(app, 'cosy_engine', None)
        details = engine.availability() if engine is not None else {}
        return {key: details[key] for key in (
            'loaded', 'device', 'precision', 'reference_cache_entries', 'compute_mode',
            'text_embedding_offloaded') if key in details}
    except Exception:
        return {}


async def main():
    import app
    for line in sys.stdin:
        try:
            request = json.loads(line)
            folder = Path(request['folder'])
            if not folder.is_dir():
                continue
        except (ValueError, TypeError, KeyError):
            # Parent-owned IPC only; never echo malformed requests or user text.
            continue

        if request.get('action') == 'preload':
            try:
                engine = getattr(app, 'cosy_engine', None)
                readiness = engine.availability() if engine is not None else {}
                if readiness.get('ready'):
                    engine._load_engine(engine.model_dir())
                result = {'runtime': runtime_snapshot(app)}
                if not readiness.get('ready'):
                    result['error'] = str(readiness.get('reason') or 'Mô hình chưa sẵn sàng để nạp trước.')[:1000]
            except Exception:
                result = {'runtime': {}, 'error': 'Chưa nạp sẵn được mô hình; lượt tạo sẽ kiểm tra lại.'}
            atomic_json(folder / 'result.json', result)
            continue

        latest_progress = {}
        control_state = {}

        def progress(info):
            if not isinstance(info, dict):
                return
            try:
                update = {
                    key: info[key] for key in ('progress', 'phase', 'completed_units',
                                             'total_units', 'generated_seconds', 'synthesized_seconds',
                                             'reused_seconds', 'cache_hits', 'active_workers',
                                             'batch_size') if key in info}
                message = info.get('message')
                if isinstance(message, str) and 0 < len(message) <= 1000:
                    update['message'] = message
                runtime = runtime_snapshot(app)
                if runtime:
                    update['runtime'] = runtime
                latest_progress.update(update)
                cooperative_checkpoint(folder, latest_progress, control_state)
                atomic_json(folder / 'progress.json', update)
            except (OSError, TypeError, ValueError):
                # An unavailable progress file must not discard generated audio.
                pass

        try:
            payload = app.Speech.model_validate(request['payload'])
            audio = folder / 'audio.bin'
            progress({'progress': 0, 'phase': 'starting', 'completed_units': 0,
                      'total_units': 0, 'generated_seconds': 0, 'active_workers': 0})
            response = await app.generate_speech(payload, progress=progress, output_path=audio)
            cooperative_checkpoint(folder, latest_progress, control_state)
            if isinstance(response, FileResponse):
                if Path(response.path).resolve() != audio.resolve():
                    raise ValueError('unexpected worker audio path')
            else:
                audio.write_bytes(response.body)
            result = {'media_type': response.media_type}
            result['runtime'] = runtime_snapshot(app)
        except HTTPException as exc:
            result = {'error': str(exc.detail)}
        except Exception:
            result = {'error': 'Bộ máy tạo giọng gặp lỗi. Kiểm tra mô hình và cấu hình dịch vụ.'}
        atomic_json(folder / 'result.json', result)
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
