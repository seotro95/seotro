"""Pasted caption metadata never becomes speech or absorbs the next cue."""
import importlib
import wave

import pytest

from narration import plan_segments
from subtitles import export_srt, parse_srt, timestamp


def test_user_timestamp_range_keeps_text_and_exact_milliseconds():
    source = '1\n00:04:28,533 -->00:04:29,333\nNyob zoo.\n'
    expected = [{'start': 268.533, 'end': 269.333, 'text': 'Nyob zoo.'}]
    assert parse_srt(source) == expected
    assert parse_srt(export_srt(parse_srt(source))) == expected
    assert [(s.cue, s.text) for s in plan_segments({'text': source, 'input_format': 'srt'})] == [(0, 'Nyob zoo.')]


@pytest.mark.parametrize('separator', ['', '\n', '\n\n'])
@pytest.mark.parametrize('indices', [True, False])
def test_timing_lines_delimit_cues_without_requiring_blank_separators(separator, indices):
    first = '00:00:00,500 -->00:00:01,300\nPab paj pav pas pag pam pad pa.'
    second = '00:00:01,300 -->00:00:02,100\nUa tsaug.'
    source = ('1\n' if indices else '') + first + '\n' + separator + ('2\n' if indices else '') + second
    cues = parse_srt(source)
    assert cues == [
        {'start': .5, 'end': 1.3, 'text': 'Pab paj pav pas pag pam pad pa.'},
        {'start': 1.3, 'end': 2.1, 'text': 'Ua tsaug.'},
    ]


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
def test_bom_zero_width_prefixes_and_line_endings_do_not_turn_indices_into_words(newline):
    source = '\ufeff1\n\n\u200b00:00:01,000 --> 00:00:02,000\n<b>Nyob zoo &amp; zoo siab.</b>\n2\n00:00:02,000 --> 00:00:03,000\nUa tsaug.'
    cues = parse_srt(source.replace('\n', newline))
    assert [cue['text'] for cue in cues] == ['Nyob zoo & zoo siab.', 'Ua tsaug.']
    assert [cue['start'] for cue in cues] == [1, 2]


@pytest.mark.parametrize('timing', [
    '00:04:28.533 --> 00:04:29.333',
    '4:28,533 -->4:29,333',
    '04:28.533 -> 04:29.333',
    '04:28.533 → 04:29.333',
    '[00:04:28,533 -->00:04:29,333]',
    '(00:04:28,533 -->00:04:29,333)',
    '"00:04:28,533 -->00:04:29,333"',
    '1 00:04:28,533 -->00:04:29,333',
])
def test_caption_range_variants_use_the_same_cue_boundaries(timing):
    assert parse_srt(f'{timing}\nNyob zoo.') == [
        {'start': 268.533, 'end': 269.333, 'text': 'Nyob zoo.'},
    ]


def test_inline_words_survive_and_webvtt_display_settings_are_metadata():
    source = '00:04:28,533 -->00:04:29,333 align:start position:0% Nyob zoo.'
    assert parse_srt(source) == [
        {'start': 268.533, 'end': 269.333, 'text': 'Nyob zoo.'},
    ]


def test_long_minute_timestamps_from_editor_exports_reach_the_three_hour_boundary():
    assert parse_srt('179:59.100 -->180:00.000\nUa tsaug.') == [
        {'start': 10799.1, 'end': 10800, 'text': 'Ua tsaug.'},
    ]


def test_real_spoken_numbers_times_and_hmong_tone_letters_stay_in_cue_text():
    words = 'Pab paj pav pas pag pam pad pa. Kuv muaj 12 tug; 200.000 thiab 12:30.'
    source = f'1\n00:00:01,000 -->00:00:02,000\n{words}\n2025\n\n2\n00:00:02,000 -->00:00:03,000\n42'
    assert [cue['text'] for cue in parse_srt(source)] == [words + '\n2025', '42']


def test_inline_numeric_caption_is_never_a_following_cue_index():
    source = '00:00:01,000 -->00:00:02,000 42\n00:00:02,000 -->00:00:03,000 Ua tsaug.'
    assert [cue['text'] for cue in parse_srt(source)] == ['42', 'Ua tsaug.']


def test_lone_numeric_body_stays_spoken_before_an_unindexed_next_cue():
    source = '00:00:01,000 -->00:00:02,000\n42\n\n00:00:02,000 -->00:00:03,000\nUa tsaug.'
    assert [cue['text'] for cue in parse_srt(source)] == ['42', 'Ua tsaug.']


@pytest.mark.parametrize('source', [
    '',
    'bad',
    '1\n00:00:01,000 -->00:00:02,000\n',
    '1\n00:00:01,000 -->00:00:02,000\n<b></b>',
    '00:00:01,000 -->00:00:00,500\nNyob zoo.',
    '00:00:01,000 -->00:00:02,000\nNyob zoo.\n2\n00:00:01,500 -->00:00:03,000\nUa tsaug.',
    '00:60:00,000 -->01:00:02,000\nNyob zoo.',
    '00:00:60,000 -->00:01:02,000\nNyob zoo.',
    '00:00:01,000 -->00:00:02,000\nNyob zoo.\n00:00:60,000 -->00:01:02,000\nUa tsaug.',
    '00:00:01,000 -->broken\nNyob zoo.',
    '00:00:01,000 -->00:00:02,000\nNyob zoo.\n00:00:02,000 -->broken\nUa tsaug.',
    '00:00:01,000 -->00:00:02,000\nNyob zoo.\n00:00:02,000 -->\nUa tsaug.',
    '03:00:00,000 -->03:00:00,001\nNyob zoo.',
])
def test_invalid_empty_overlapping_and_out_of_bounds_cues_are_rejected(source):
    with pytest.raises(ValueError):
        parse_srt(source)


def test_cue_count_limit_still_applies_without_blank_separators():
    source = '\n'.join(f'{index + 1}\n{timestamp(index / 10)} -->{timestamp(index / 10 + .05)}\nNyob zoo.' for index in range(10001))
    with pytest.raises(ValueError, match='10.000'):
        parse_srt(source)


def test_worker_synthesizes_only_words_for_srt_without_blank_separators(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STUDIO_DATA_DIR', str(tmp_path))
    worker = importlib.import_module('worker')
    monkeypatch.setattr(worker, 'DATA', tmp_path)
    (tmp_path / 'audio').mkdir()
    received = []

    def synthesize(text, output):
        received.append(text)
        with wave.open(str(output), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(b'\x00\x20' * 6000)

    source = '1\n00:00:00,533 -->00:00:01,333\nPab paj pav pas pag pam pad pa.\n2\n00:00:01,333 -->00:00:02,133\nUa tsaug.'
    worker.render({'id': 'unseparated-captions', 'text': source, 'input_format': 'srt',
                   'engine': 'vieneu', 'format': 'wav', 'speed': 1}, synthesize)
    assert received == ['Pab paj pav pas pag pam pad pa.', 'Ua tsaug.']
    assert parse_srt((tmp_path / 'audio' / 'unseparated-captions.srt').read_text()) == parse_srt(source)
    with wave.open(str(tmp_path / 'audio' / 'unseparated-captions.wav')) as audio:
        assert audio.getnframes() == round(2.133 * 24000)
