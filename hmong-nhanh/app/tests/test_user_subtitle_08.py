"""The user's copied TXT/SRT sample reaches synthesis as dialogue only."""
import io
from types import SimpleNamespace
import wave

import pytest

from documents import parse_document
import longform


WORDS = 'Tae-yong cov ntaub ntawv tus kheej'
USER_BLOCK = '217\n00:06:07,200 --> 00:06:08,400\n' + WORDS


@pytest.mark.parametrize('left,right', [('', ''), ('"', '"'), ("'", "'"), ('“', '”'), ('‘', '’')])
def test_exact_user_block_copied_with_optional_quotes(left, right):
    parsed = parse_document(left + USER_BLOCK + right, timing='fit')
    assert parsed['text'] == WORDS
    assert parsed['cues'] == [{'start': 367.2, 'end': 368.4, 'text': WORDS}]
    assert parsed['timed'] and parsed['duration'] == 368.4


def test_windows_txt_line_endings_and_nonsequential_ids_keep_dialogue_numbers():
    raw = '\ufeff' + (USER_BLOCK + ' 217\n\n982\n00:06:09,000 --> 00:06:10,000\n2026').replace('\n', '\r\n')
    parsed = parse_document(raw, timing='fit')
    assert [cue['text'] for cue in parsed['cues']] == [WORDS + ' 217', '2026']
    assert parsed['text'] == WORDS + ' 217\n\n2026'


@pytest.mark.parametrize('raw', [
    '“00:06:07,200 --> 00:06:08,400\n' + WORDS + '”',
    '“00:06:07,200 --> 00:06:08,400”\n' + WORDS,
    '06:07.200 → 06:08.400 ' + WORDS,
])
def test_txt_timestamp_forms_keep_name_hyphen(raw):
    parsed = parse_document(raw, timing='natural')
    assert parsed['text'] == WORDS
    assert not parsed['timed']


def test_smart_quotes_do_not_remove_ordinary_dialogue_or_read_broken_times():
    plain = '“217 Tae-yong hais 2026.”'
    assert parse_document(plain)['text'] == plain
    with pytest.raises(ValueError, match='mốc'):
        parse_document('“00:06:xx --> 00:06:08,400”\n' + WORDS)


def _wave_bytes(seconds):
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(b'\x01\x02' * round(seconds * 24000))
    return output.getvalue()


@pytest.mark.parametrize('timing', ['fit', 'natural'])
def test_user_sample_reaches_engine_without_metadata_and_keeps_requested_timeline(tmp_path, monkeypatch, timing):
    reference = tmp_path / 'reference.wav'
    reference.write_bytes(_wave_bytes(3))
    payload = {'text': '"' + USER_BLOCK + '"', 'voice': 'hmong-white-female',
               'quality': 'balanced', 'style': 'natural', 'speed': 1, 'timing': timing,
               '_reference': {'path': str(reference), 'text': 'Exact reference words.'}}
    longform.atomic_json(tmp_path / 'input.json', payload)
    calls = []

    def synthesize(text, speed, path, transcript, quality):
        calls.append((text, speed, path, transcript, quality))
        return _wave_bytes(1.2)

    monkeypatch.setattr(longform.cloning_engine, 'synthesize', synthesize)
    monkeypatch.setattr(longform.cloning_engine, 'runtime_device', lambda: 'cpu')
    monkeypatch.setattr(longform.shutil, 'disk_usage', lambda _: SimpleNamespace(free=2 * 1024 ** 3))
    result = longform.process_job(tmp_path)
    assert calls == [(WORDS, 1, reference, 'Exact reference words.', 'balanced')]
    expected_seconds = 368.4 if timing == 'fit' else 1.2
    assert result['audio_seconds'] == expected_seconds
    assert result['target_seconds'] == (368.4 if timing == 'fit' else None)
    path = tmp_path / 'parts' / result['parts'][0]['filename']
    with wave.open(str(path), 'rb') as audio:
        assert audio.getnframes() == round(expected_seconds * 24000)
        if timing == 'fit':
            assert audio.readframes(round(367.2 * 24000)) == bytes(round(367.2 * 24000) * 2)
        assert audio.readframes(round(1.2 * 24000)) == b'\x01\x02' * round(1.2 * 24000)
