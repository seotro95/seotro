"""Read subtitle words continuously without imposing short caption windows."""
import importlib
import json
import wave

import pytest

import longform
from narration import Segment, plan_segments
from subtitles import parse_srt


USER_SRT = ('217\n00:06:07,200 --> 00:06:08,400\n'
            'Tae-yong cov ntaub ntawv tus kheej')
USER_WORDS = 'Tae-yong cov ntaub ntawv tus kheej'


@pytest.mark.parametrize('engine', ['vieneu', 'hmong_native', 'f5_hmong'])
def test_speech_only_keeps_exact_user_words_without_cue_numbers(engine):
    job = {'text': USER_SRT, 'input_format': 'srt', 'engine': engine,
           'subtitle_timing': False, 'paragraph_pause': 0}
    segments = plan_segments(job)
    assert [segment.text for segment in segments] == [USER_WORDS]
    assert all(segment.cue is None for segment in segments)
    assert job['text'] == USER_SRT and job['input_format'] == 'srt'


def test_omitted_and_explicit_true_preserve_timed_cue_plan():
    job = {'text': USER_SRT, 'input_format': 'srt'}
    expected = [Segment(text=USER_WORDS, cue=0)]
    assert plan_segments(job) == expected
    assert plan_segments({**job, 'subtitle_timing': True}) == expected


def test_speech_only_does_not_strip_a_spoken_time_from_cue_body():
    source = '217\n00:06:07,200 -->00:06:08,400\n12:30 yog lub sij hawm.'
    segments = plan_segments({'text': source, 'input_format': 'srt', 'subtitle_timing': False})
    assert ' '.join(segment.text for segment in segments) == '12:30 yog lub sij hawm.'


def test_controls_and_prose_numbers_are_planned_as_continuous_hmong_speech():
    source = (USER_SRT + '\n\n218\n00:06:09,000 -->00:06:10,200\n'
              '[emotion=warm]Kuv muaj 2 tug. [pause=0.5] **Ua tsaug.**')
    segments = plan_segments({'text': source, 'input_format': 'srt', 'subtitle_timing': False,
        'engine': 'hmong_native', 'segment_plan': 'hmong-expression-v1',
        'hmong_phrase_context': True, 'paragraph_pause': 0, 'auto_rhythm': False})
    assert all(segment.cue is None for segment in segments)
    assert ' '.join(segment.text for segment in segments if segment.text) == (
        USER_WORDS + ' Kuv muaj ob tug. Ua tsaug.')
    assert [segment.pause for segment in segments if not segment.text] == [.5]
    assert any(segment.emphasis and segment.text == 'Ua tsaug.' for segment in segments)


@pytest.mark.parametrize('extra', [{'video_id': 'a' * 32}, {'character_cast': {'version': 1}}])
def test_speech_only_rejects_timeline_dependent_work(extra):
    with pytest.raises(ValueError, match='giữ mốc thời gian'):
        plan_segments({'text': USER_SRT, 'input_format': 'srt', 'subtitle_timing': False, **extra})


def test_worker_speaks_full_sentence_without_six_minutes_of_padding(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    words = []

    def synthesize(text, path):
        words.append(text)
        with wave.open(str(path), 'wb') as stream:
            stream.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\x10\x20' * 57600)  # Complete phrase lasts 2.4s.

    job = {'id': 'a' * 32, 'text': USER_SRT, 'input_format': 'srt',
           'subtitle_timing': False, 'engine': 'vieneu', 'format': 'wav',
           'speed': 1, 'paragraph_pause': 0}
    worker.render(job, synthesize)
    assert words == [USER_WORDS]
    assert job['text'] == USER_SRT and job['input_format'] == 'srt'
    with wave.open(str(tmp_path / 'audio' / (job['id'] + '.wav'))) as stream:
        assert stream.getnframes() == 57600
    generated = parse_srt((tmp_path / 'audio' / (job['id'] + '.srt')).read_text())
    assert generated == [{'start': 0, 'end': 2.4, 'text': USER_WORDS}]
    assert not (tmp_path / 'parts' / job['id'] / 'alignment.json').exists()
    result = json.loads((tmp_path / 'parts' / job['id'] / 'result.json').read_text())
    assert result['duration_limited'] is False and result['completed'] == result['total'] == 1
    # Legacy timed mode still protects words by reporting an impossible fit.
    with pytest.raises(ValueError, match='Câu SRT 1 đọc quá dài'):
        worker.render({**job, 'id': 'b' * 32, 'subtitle_timing': True}, synthesize)
    failed_alignment = tmp_path / 'parts' / ('b' * 32) / 'alignment.json'
    assert failed_alignment.exists()
    worker.render({**job, 'id': 'b' * 32}, synthesize)
    assert not failed_alignment.exists()
    with wave.open(str(tmp_path / 'audio' / ('b' * 32 + '.wav'))) as stream:
        assert stream.getnframes() == 57600


def test_chunk_identity_binds_speech_only_and_keeps_legacy_true_hash(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    job = {'engine': 'hmong_native', 'input_format': 'srt',
           'hmong_voice_snapshot': {'voice_id': 'hmong-male'}, 'speed': 1}
    segment = Segment(text=USER_WORDS)
    old = worker._chunk_identity(job, segment)
    assert old == worker._chunk_identity({**job, 'subtitle_timing': True}, segment)
    assert old != worker._chunk_identity({**job, 'subtitle_timing': False}, segment)


def test_chapter_identity_preserves_legacy_txt_and_binds_subtitle_mode():
    job = {'text': USER_WORDS, 'engine': 'hmong_native', 'input_format': 'txt',
           'language': 'mww', 'format': 'wav'}
    chapters = longform.plan_chapters(job)
    identity = longform.plan_identity(job, chapters)
    assert identity == longform.plan_identity({**job, 'subtitle_timing': True}, chapters)
    assert identity == longform.plan_identity({**job, 'subtitle_timing': False}, chapters)
    timed = {**job, 'input_format': 'srt'}
    assert longform.plan_identity(timed, chapters) != longform.plan_identity(
        {**timed, 'subtitle_timing': False}, chapters)
