"""Long scripts stay bounded, ordered, resumable and honest about throughput."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

import longform


def audio(seconds=.2, value=513):
    stream = io.BytesIO()
    with wave.open(stream, 'wb') as sound:
        sound.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        sound.writeframes(value.to_bytes(2, 'little', signed=True) * round(seconds * 24000))
    return stream.getvalue()


def frames(path):
    with wave.open(str(path), 'rb') as sound:
        return sound.readframes(sound.getnframes())


def script(count=9):
    # Distinct sentences make dropped/reordered/resynthesized segments observable.
    return ' '.join(f'{number:02d} ' + 'lus ' * 42 + '.' for number in range(count))


@pytest.fixture
def folder(tmp_path, monkeypatch):
    sample = tmp_path / 'reference.wav'
    sample.write_bytes(audio(4))
    payload = {'text': script(), 'voice': 'hmong-white-female', 'quality': 'fast',
               'style': 'natural', 'speed': 1.0,
               '_reference': {'path': str(sample), 'text': 'Exact reference transcript.'}}
    longform.atomic_json(tmp_path / 'input.json', payload)
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=1024 ** 3))
    monkeypatch.setattr(longform.cloning_engine, 'runtime_device', lambda: 'cpu')
    return tmp_path


@pytest.mark.parametrize('text', [
    '𐐀' * 1_000_000,
    ('Nyob zoo! Hmoob dawb.\n' * 50_000)[:1_000_000],
])
def test_million_unicode_characters_are_bounded_without_text_loss(text):
    assert len(text) == 1_000_000
    plan = longform.plan_text(text)
    assert all(0 < len(item['text']) <= 350 for item in plan)
    assert ''.join(''.join(item['text'].split()) for item in plan) == ''.join(text.split())
    assert plan[-1]['pause'] == 0
    assert len(plan) < 10_000


@pytest.mark.parametrize('text', ['', ' \n\t ', '𐐀' * 1_000_001, None])
def test_empty_and_oversized_text_rejected(text):
    with pytest.raises(ValueError, match='1.000.000'):
        longform.plan_text(text)


@pytest.mark.parametrize('limit', [0, -1, True, .5])
def test_invalid_chunk_limit_rejected(limit):
    with pytest.raises(ValueError, match='số nguyên dương'):
        longform.plan_text('Nyob zoo.', limit=limit)


def test_styles_keep_words_and_change_sentence_and_paragraph_pauses():
    text = ('lus ' * 43 + '.\n') + ('Hmoob ' * 30 + '. ') + 'Nyob zoo.'
    natural = longform.plan_text(text, 'natural')
    story = longform.plan_text(text, 'storytelling')
    review = longform.plan_text(text, 'film_review')
    assert [part['text'] for part in natural] == [part['text'] for part in story] == [part['text'] for part in review]
    assert [part['pause'] for part in natural] == [.3, .12, 0]
    assert [part['pause'] for part in story] == [.6, .25, 0]
    assert [part['pause'] for part in review] == [.3, .1, 0]
    with pytest.raises(ValueError, match='Kiểu đọc'):
        longform.plan_text(text, 'invented')


def test_chapter_copy_streams_fixed_size_blocks(tmp_path, monkeypatch):
    (tmp_path / 'parts').mkdir()
    chunks = [tmp_path / f'{i}.wav' for i in range(3)]
    for i, chunk in enumerate(chunks):
        chunk.write_bytes(audio(4, i + 1))
    expected = b''.join(frames(chunk) for chunk in chunks)
    requests = []
    original = wave.Wave_read.readframes
    def readframes(self, size):
        requests.append(size)
        return original(self, size)
    monkeypatch.setattr(wave.Wave_read, 'readframes', readframes)
    chapter = longform.make_chapter(tmp_path, 1, chunks)
    assert requests and set(requests) == {65536}
    assert chapter['seconds'] == 12
    monkeypatch.setattr(wave.Wave_read, 'readframes', original)
    assert frames(tmp_path / 'parts' / chapter['filename']) == expected
    assert not list(tmp_path.rglob('*.pending'))


def test_job_uses_real_style_quality_and_excludes_pauses_from_throughput(folder, monkeypatch):
    payload = json.loads((folder / 'input.json').read_text())
    payload.update(style='storytelling', quality='draft', speed=1.5)
    longform.atomic_json(folder / 'input.json', payload)
    calls = []
    def synthesize(text, speed, reference, transcript, quality):
        calls.append((text, speed, reference, transcript, quality))
        return audio(value=len(calls))
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synthesize)
    monkeypatch.setattr(longform, 'CHAPTER_SECONDS', 1)
    result = longform.process_job(folder)
    planned = longform.plan_text(payload['text'], payload['style'])
    assert [call[0] for call in calls] == [item['text'] for item in planned]
    assert all(call[1] == pytest.approx(1.41) and call[4] == 'draft' for call in calls)
    assert all(call[2] == folder / 'reference.wav' and call[3] == 'Exact reference transcript.' for call in calls)
    assert result['progress'] == 100 and result['completed'] == result['total'] == len(planned)
    assert result['device'] == 'cpu' and result['effective_speed'] == pytest.approx(1.41)
    saved = json.loads((folder / 'checkpoint.json').read_text())
    assert saved['spoken_seconds'] == pytest.approx(.2 * len(planned))
    assert result['audio_seconds'] > saved['spoken_seconds']
    # Rounded display time can lose milliseconds; compare the underlying ratio.
    measured_time = saved['spoken_seconds'] / result['throughput']
    assert abs(measured_time - result['elapsed_seconds']) <= .00051
    assert result['estimated_seconds_for_hour'] == pytest.approx(3600 / result['throughput'])
    assert all(part['seconds'] <= 1 for part in result['parts'])
    actual = b''.join(frames(folder / 'parts' / part['filename']) for part in result['parts'])
    expected = b''.join(frames(path) for path in sorted((folder / 'chunks').glob('*.wav')))
    assert actual == expected


def test_resume_skips_finished_chunks_and_preserves_audio_order(folder, monkeypatch):
    calls = []
    def synthesize(text, *args, **kwargs):
        calls.append(text)
        if len(calls) == 4:
            raise RuntimeError('interrupted synthesis')
        return audio(value=int(text[:2]) + 1)
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synthesize)
    monkeypatch.setattr(longform, 'CHAPTER_SECONDS', .7)
    with pytest.raises(RuntimeError, match='interrupted'):
        longform.process_job(folder)
    assert not (folder / 'result.json').exists()
    saved = json.loads((folder / 'checkpoint.json').read_text())
    assert saved['completed'] == 3
    originals = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (folder / 'chunks').glob('*.wav')}
    first_part = folder / 'parts' / 'part-0001.wav'
    first_modified = first_part.stat().st_mtime_ns
    result = longform.process_job(folder)
    assert result['resumed'] and result['progress'] == 100
    planned = longform.plan_text(json.loads((folder / 'input.json').read_text())['text'])
    assert calls[:3] == [item['text'] for item in planned[:3]]
    assert calls[4:] == [item['text'] for item in planned[3:]]
    assert len(calls) == len(planned) + 1  # Only the interrupted segment is retried.
    assert all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in originals.items())
    assert first_part.stat().st_mtime_ns == first_modified
    assert all(part['seconds'] <= .7 for part in result['parts'])
    assert b''.join(frames(folder / 'parts' / part['filename']) for part in result['parts']) == b''.join(
        frames(path) for path in sorted((folder / 'chunks').glob('*.wav')))


@pytest.mark.parametrize('change', ['text', 'voice', 'style', 'quality', 'speed', 'reference_text', 'sample'])
def test_resume_rejects_changed_source_before_generating(folder, monkeypatch, change):
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *args, **kwargs: audio())
    longform.process_job(folder)
    payload = json.loads((folder / 'input.json').read_text())
    if change == 'reference_text':
        payload['_reference']['text'] += ' changed'
    elif change == 'sample':
        (folder / 'reference.wav').write_bytes(audio(4, 100))
    else:
        payload[change] = {'text': 'Changed text.', 'voice': 'hmong-white-male', 'style': 'film_review', 'quality': 'quality', 'speed': .8}[change]
    longform.atomic_json(folder / 'input.json', payload)
    def forbidden(*args, **kwargs):
        raise AssertionError('must reject settings before synthesis')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', forbidden)
    with pytest.raises(ValueError, match='Thiết lập khác'):
        longform.process_job(folder)


def test_missing_finished_chunk_fails_without_overwriting_good_chunks(folder, monkeypatch):
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *args, **kwargs: audio())
    longform.process_job(folder)
    good = folder / 'chunks' / 'chunk-000000.wav'
    original = good.read_bytes()
    (folder / 'chunks' / 'chunk-000001.wav').unlink()
    with pytest.raises(ValueError, match='thiếu/hỏng'):
        longform.process_job(folder)
    assert good.read_bytes() == original


@pytest.mark.parametrize('field,value', [('completed', 1.2), ('completed', True), ('elapsed_seconds', -1), ('spoken_seconds', float('nan'))])
def test_invalid_checkpoint_metrics_are_rejected(folder, monkeypatch, field, value):
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *args, **kwargs: audio())
    longform.process_job(folder)
    path = folder / 'checkpoint.json'
    data = json.loads(path.read_text())
    data[field] = value
    longform.atomic_json(path, data)
    with pytest.raises(ValueError, match='Checkpoint không hợp lệ'):
        longform.process_job(folder)


def test_low_disk_stops_before_synthesis_and_can_resume(folder, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('low disk must stop before synthesis')
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', forbidden)
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=99 * 1024 ** 2))
    with pytest.raises(ValueError, match='100 MB'):
        longform.process_job(folder)
    assert not (folder / 'result.json').exists()
    assert not list((folder / 'chunks').iterdir())
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=1024 ** 3))
    monkeypatch.setattr(longform.cloning_engine, 'synthesize', lambda *args, **kwargs: audio())
    assert longform.process_job(folder)['progress'] == 100


def test_truncated_engine_audio_is_not_persisted(tmp_path):
    destination = tmp_path / 'chunk.wav'
    with pytest.raises(ValueError, match='chưa đầy đủ'):
        longform.write_chunk(destination, audio()[:-4], .1)
    assert not destination.exists()
    assert not list(tmp_path.glob('*.pending'))
