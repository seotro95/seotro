"""Million-character coverage and durable, all-or-nothing chapter exports."""
import json
import importlib
import shutil
import threading
import time
import wave
import zipfile
from dataclasses import asdict

import pytest

import longform
from narration import Segment, plan_segments
from state_io import write_json_atomic


def job(**changes):
    return {'id': 'a' * 32, 'text': 'Nyob zoo. ' * 2600, 'engine': 'f5_hmong',
            'language': 'mww', 'voice_id': 'hmong-male', 'speaker': 'hmong-male',
            'input_format': 'txt', 'format': 'wav', 'segment_plan': 'hmong-expression-v1',
            'hmong_phrase_context': True, 'auto_rhythm': False, 'paragraph_pause': 0,
            'emotion': 'warm', 'emotion_strength': .65, 'speed': 1, **changes}


def pcm(path, frames=2400):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(24000)
        stream.writeframes(b'\x10\x00' * frames)


class Worker:
    """Obeys the actual worker's disk and private preplanned-segment contract."""
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.fail = None
        self.limited = False

    def __call__(self, path, env, work):
        child = json.loads(path.read_text(encoding='utf-8'))
        self.calls.append(child)
        assert path.parent.parent == self.root / 'parts' / ('a' * 32) / 'chapters'
        assert path.name == 'job.json'
        assert child['max_minutes'] == 180
        assert child['input_format'] == 'txt'
        assert child['_longform_parent_id'] == 'a' * 32
        assert len(child['_longform_identity']) == 64
        assert len(child['text']) <= 11000
        work.mkdir(parents=True, exist_ok=True)
        # A tiny retained marker stands for real bounded waveform checkpoints.
        (work / '000000.wav').write_bytes(b'checkpoint')
        if self.fail == len(self.calls):
            write_json_atomic(work / 'worker-done.json', {'code': 1, 'user_error': 'Interrupted test chapter'})
            return 1
        output = self.root / 'audio' / (child['id'] + '.' + child['format'])
        pcm(output)
        spoken = [part['text'] for part in child['_PREPLANNED_SEGMENTS'] if part['text']]
        (self.root / 'audio' / (child['id'] + '.srt')).write_text(
            '1\n00:00:00,000 --> 00:00:00,100\n' + ' '.join(spoken) + '\n', encoding='utf-8')
        total = len(child['_PREPLANNED_SEGMENTS'])
        write_json_atomic(work / 'result.json', {
            'completed': total, 'total': total, 'duration_limited': self.limited,
            'audio_seconds': .1, 'spoken_audio_seconds': .08, 'inserted_silence_seconds': .02})
        return 0


def test_actual_million_characters_preserves_all_planned_hmong_and_controls():
    # Exactly one million Unicode characters, not a mocked large input limit.
    unit = '[emotion=sad] Nyob **zoo**. [pause=0] Kuv nyob ntawm no. [emotion=warm] '
    source = (unit * (1_000_000 // len(unit)))
    source += 'a' * (1_000_000 - len(source))
    parent = job(text=source)
    segments = plan_segments(parent)
    chapters = longform.plan_chapters(parent, segments)
    assert len(source) == longform.MAX_CHARACTERS
    assert len(chapters) > 30
    assert all(chapter.characters <= longform.PART_CHARACTERS for chapter in chapters)
    assert [asdict(part) for chapter in chapters for part in chapter.segments] == [asdict(part) for part in segments]
    assert chapters[0].start == 0
    assert chapters[-1].end == len(segments)
    assert all(left.end == right.start for left, right in zip(chapters, chapters[1:]))
    assert any(segment.emphasis for segment in segments)
    assert any(not segment.text and segment.pause == 0 for segment in segments)
    assert {segment.emotion for segment in segments if segment.text} == {'warm', 'sad'}


def test_partition_preserves_persistent_emotion_and_exact_segment_fields():
    parent = job(text='[emotion=sad] ' + 'Kuv tu siab. ' * 1500 + '[pause=1.5] [emotion=joyful] **Zoo kawg.**')
    original = plan_segments(parent)
    expected = [asdict(segment) for segment in original]
    chapters = longform.plan_chapters(parent, original)
    assert len(chapters) > 1
    assert chapters[1].segments[0].emotion == 'sad'
    assert [asdict(segment) for chapter in chapters for segment in chapter.segments] == expected
    chapters[0].segments[0].text = 'changed copy'
    assert [asdict(segment) for segment in original] == expected


def test_zip64_contains_every_part_exact_source_and_manifest(tmp_path):
    source = '  \r\n' + job()['text'] + '\r\n '
    parent = job(text=source)
    worker = Worker(tmp_path)
    result = longform.run_longform(parent, tmp_path, worker, {})
    assert result['completed'] == result['total']
    assert result['duration_limited'] is False
    assert result['chapter_count'] == len(worker.calls) >= 3
    assert result['audio_seconds'] == pytest.approx(.1 * len(worker.calls))
    assert result['reused_chapters'] == 0
    assert not (tmp_path / 'audio' / (parent['id'] + '.wav')).exists()
    with zipfile.ZipFile(tmp_path / 'audio' / (parent['id'] + '.zip')) as archive:
        assert archive.read('original.txt').decode('utf-8') == source
        manifest = json.loads(archive.read('manifest.json'))
        assert manifest['source_characters'] == len(source)
        assert manifest['completed'] == manifest['total']
        assert len(archive.namelist()) == 2 + result['chapter_count'] * 3
        for chapter in result['chapters']:
            for path in chapter['files'].values():
                assert path in archive.namelist()
            transcript = archive.read(chapter['files']['txt']).decode('utf-8')
            actual = worker.calls[chapter['index'] - 1]['_PREPLANNED_SEGMENTS']
            assert transcript == '\n'.join(segment['text'] for segment in actual if segment['text']) + '\n'
            assert archive.getinfo(chapter['files']['audio']).extract_version >= 45
    assert not list((tmp_path / 'parts').glob('*/000000.wav'))
    assert not list((tmp_path / 'audio').glob('*.srt'))
    # read_text() would normalize CRLF and incorrectly reject this exact-source
    # resume, especially when the portable Windows build created the file.
    assert longform.run_longform(parent, tmp_path, worker, {})['reused_chapters'] == result['chapter_count']


def test_failed_chapter_resume_keeps_complete_audio_and_partial_chunk_cache(tmp_path):
    parent = job()
    worker = Worker(tmp_path)
    worker.fail = 2
    with pytest.raises(RuntimeError, match='Interrupted test chapter'):
        longform.run_longform(parent, tmp_path, worker, {})
    first = tmp_path / 'parts' / parent['id'] / 'chapters' / '0001' / 'audio.wav'
    assert first.is_file()
    before = first.read_bytes()
    failed_id = worker.calls[1]['id']
    assert (tmp_path / 'parts' / failed_id / '000000.wav').read_bytes() == b'checkpoint'
    assert not (tmp_path / 'audio' / (parent['id'] + '.zip')).exists()
    worker.fail = None
    result = longform.run_longform({**parent, 'status': 'queued', 'progress': 40}, tmp_path, worker, {})
    assert result['reused_chapters'] == 1
    assert first.read_bytes() == before
    assert worker.calls[2]['id'] == failed_id
    assert not (tmp_path / 'parts' / failed_id).exists()


@pytest.mark.parametrize('change', [{'speed': 1.2}, {'text': 'Nyob zoo.'}, {'emotion': 'sad'},
                                   {'hmong_reference_fingerprint': 'changed'}])
def test_resume_rejects_changed_source_or_settings_without_touching_outputs(tmp_path, change):
    parent = job()
    worker = Worker(tmp_path)
    worker.fail = 2
    with pytest.raises(RuntimeError):
        longform.run_longform(parent, tmp_path, worker, {})
    first = tmp_path / 'parts' / parent['id'] / 'chapters' / '0001' / 'audio.wav'
    before = first.read_bytes()
    with pytest.raises(ValueError, match='đã thay đổi'):
        longform.run_longform({**parent, **change}, tmp_path, worker, {})
    assert first.read_bytes() == before
    assert len(worker.calls) == 2


def test_parent_cancel_propagates_to_active_child_and_preserves_checkpoint(tmp_path):
    parent = job()
    started = threading.Event()
    parentwork = tmp_path / 'parts' / parent['id']
    observed = []

    def cancelled_worker(path, env, work):
        (work / '000000.wav').write_bytes(b'checkpoint')
        started.set()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if (work / 'cancel.flag').exists():
                observed.append(work)
                return -2
            time.sleep(.01)
        raise AssertionError('Parent cancellation did not reach the active worker')

    def cancel_parent():
        assert started.wait(3)
        (parentwork / 'cancel.flag').touch()

    canceller = threading.Thread(target=cancel_parent)
    canceller.start()
    try:
        with pytest.raises(InterruptedError, match='Đã dừng'):
            longform.run_longform(parent, tmp_path, cancelled_worker, {})
    finally:
        canceller.join()
    assert observed
    assert (observed[0] / '000000.wav').is_file()
    assert not (tmp_path / 'audio' / (parent['id'] + '.zip')).exists()


@pytest.mark.parametrize('failure', ['limited', 'incomplete', 'missing_srt', 'truncated_wav'])
def test_never_publishes_limited_incomplete_or_truncated_audio(tmp_path, failure):
    parent = job(text='Nyob zoo.')
    worker = Worker(tmp_path)

    def invalid_worker(path, env, work):
        code = worker(path, env, work)
        child = worker.calls[-1]
        result_path = work / 'result.json'
        result = json.loads(result_path.read_text())
        if failure == 'limited':
            result['duration_limited'] = True
        elif failure == 'incomplete':
            result['completed'] = 0
        elif failure == 'missing_srt':
            (tmp_path / 'audio' / (child['id'] + '.srt')).unlink()
        else:
            audio = tmp_path / 'audio' / (child['id'] + '.wav')
            with audio.open('r+b') as stream:
                stream.truncate(60)
        write_json_atomic(result_path, result)
        return code

    with pytest.raises(ValueError):
        longform.run_longform(parent, tmp_path, invalid_worker, {})
    assert not (tmp_path / 'audio' / (parent['id'] + '.zip')).exists()
    assert not (tmp_path / 'parts' / parent['id'] / 'result.json').exists()
    assert not (tmp_path / 'parts' / parent['id'] / 'chapters' / '0001' / 'complete.json').exists()


def test_corrupt_completed_chapter_is_regenerated_instead_of_reused(tmp_path):
    parent = job(text='Nyob zoo.')
    worker = Worker(tmp_path)
    longform.run_longform(parent, tmp_path, worker, {})
    audio = tmp_path / 'parts' / parent['id'] / 'chapters' / '0001' / 'audio.wav'
    with audio.open('r+b') as stream:
        stream.truncate(60)
    result = longform.run_longform(parent, tmp_path, worker, {})
    assert result['reused_chapters'] == 0
    assert len(worker.calls) == 2
    assert audio.stat().st_size > 60


def test_cancel_during_archive_retains_chapters_and_removes_temporary_zip(tmp_path, monkeypatch):
    parent = job(text='Nyob zoo.')
    worker = Worker(tmp_path)
    original = longform._zip_file

    def cancel_archive(archive, path, name, check_cancel):
        original(archive, path, name, check_cancel)
        (tmp_path / 'parts' / parent['id'] / 'cancel.flag').touch()

    monkeypatch.setattr(longform, '_zip_file', cancel_archive)
    with pytest.raises(InterruptedError):
        longform.run_longform(parent, tmp_path, worker, {})
    parentwork = tmp_path / 'parts' / parent['id']
    assert (parentwork / 'chapters' / '0001' / 'complete.json').is_file()
    assert not (parentwork / 'archive.zip.tmp').exists()
    assert not (tmp_path / 'audio' / (parent['id'] + '.zip')).exists()
    (parentwork / 'cancel.flag').unlink()
    monkeypatch.setattr(longform, '_zip_file', original)
    assert longform.run_longform(parent, tmp_path, worker, {})['reused_chapters'] == 1
    assert len(worker.calls) == 1


@pytest.mark.parametrize('changes', [{'text': 'a' * 1_000_001}, {'engine': 'vieneu'},
                                    {'input_format': 'srt'}, {'video_id': 'b' * 32},
                                    {'text': '[pause=1]'}])
def test_invalid_longform_scope_is_rejected(changes):
    with pytest.raises(ValueError):
        longform.plan_chapters(job(**changes))


def test_reference_changes_rejected_before_any_work_directory_mutation(tmp_path):
    parent = job(hmong_voice_snapshot={'voice_id': 'changed'})
    with pytest.raises(ValueError):
        longform.run_longform(parent, tmp_path, Worker(tmp_path), {})
    assert not (tmp_path / 'parts').exists()


def test_real_worker_private_preplan_runs_all_chapters_without_model_inference(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    monkeypatch.setattr(worker, 'normalize_audio', lambda raw, temporary, tempo, gain: shutil.copyfile(raw, temporary))
    (tmp_path / 'audio').mkdir()
    parent = job(text='[emotion=sad] ' + 'Kuv nyob ntawm no. ' * 1200 + '[pause=0.2] **Nyob zoo.**',
                 voice_id='custom-test', speaker=None)
    expected = plan_segments(parent)
    spoken = []
    private_requests = []

    def synthesize(text, path):
        spoken.append(text)
        pcm(path)

    def execute(path, env, work):
        child = worker._load_worker_request(path)
        assert child is not None, 'Actual resident worker must accept controller private paths'
        private_requests.append(child)
        worker.render(child, synthesize=synthesize)
        return 0

    result = longform.run_longform(parent, tmp_path, execute, {})
    assert result['chapter_count'] >= 3
    assert spoken == [segment.text for segment in expected if segment.text]
    assert [row for child in private_requests for row in child['_PREPLANNED_SEGMENTS']] == [asdict(segment) for segment in expected]
    assert all(child['_PREPLANNED_SEGMENTS'][0]['emotion'] == 'sad' for child in private_requests)
    assert result['completed'] == len(expected)
    assert result['duration_limited'] is False
