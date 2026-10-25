"""Structural subtitle fields disappear, spoken numbers and words survive."""
import pytest

from documents import parse_document


def test_user_timestamp_is_timing_not_speech_and_spoken_numbers_survive():
    result = parse_document('1\n00:04:28,533 --> 00:04:29,333\nKuv muaj 25 xyoo.\n')
    assert result == {'format': 'srt', 'text': 'Kuv muaj 25 xyoo.',
                      'cues': [{'start': 268.533, 'end': 269.333, 'text': 'Kuv muaj 25 xyoo.'}],
                      'duration': 269.333, 'timed': True, 'warnings': []}


def test_bom_crlf_multiline_missing_blanks_and_numeric_dialogue():
    raw = '\ufeff1\r\n00:00:01,000 --> 00:00:03,500\r\nNyob zoo 2024.\r\nKuv muaj 2 tug.\r\n2\r\n00:00:04,000 --> 00:00:05,000\r\n100\r\n'
    result = parse_document(raw)
    assert result['text'] == 'Nyob zoo 2024.\nKuv muaj 2 tug.\n\n100'
    assert [cue['text'] for cue in result['cues']] == ['Nyob zoo 2024.\nKuv muaj 2 tug.', '100']
    assert result['duration'] == 5


def test_unnumbered_cues_do_not_steal_numeric_dialogue_before_next_time():
    raw = '00:00:01 --> 00:00:02\n42\n00:00:03 --> 00:00:04\n50'
    assert [cue['text'] for cue in parse_document(raw)['cues']] == ['42', '50']


def test_vtt_metadata_identifiers_settings_and_markup_are_not_spoken():
    raw = r'''WEBVTT Example
Kind: captions
Language: hmn

NOTE ignore this metadata 123
and this line

STYLE
::cue { color: red }

REGION
id: main

first-cue
00:01.000 --> 00:02.500 align:start position:0%
<v Roger><c.red><b>Nyob zoo 2</b></c></v>

second-cue
00:03.000 --> 00:05.000
<00:03.100><i>Kuv &amp; koj</i> {\an8}2025
'''
    result = parse_document(raw)
    assert result['format'] == 'vtt'
    assert result['text'] == 'Nyob zoo 2\n\nKuv & koj 2025'
    assert result['duration'] == 5


@pytest.mark.parametrize('clock,start,end', [
    ('00:04:28,533 --> 00:04:29,333', 268.533, 269.333),
    ('04:28.533 --> 04:29.333', 268.533, 269.333),
    ('4:28.5 -> 4:29.33', 268.5, 269.33),
    ('00:04:28 → 00:04:29', 268, 269),
    ('"00:04:28,533 --> 00:04:29,333"', 268.533, 269.333),
    ('[00:04:28,533 --> 00:04:29,333]', 268.533, 269.333),
])
def test_common_range_forms(clock, start, end):
    cue = parse_document(clock + '\nNqe 123.')['cues'][0]
    assert cue == {'start': start, 'end': end, 'text': 'Nqe 123.'}


def test_txt_inline_ranges_keep_inline_dialogue_and_number():
    result = parse_document('00:00:01.000 --> 00:00:02.000 Kuv muaj 2 tug.\n00:00:03 --> 00:00:05 Nyob zoo.')
    assert result['text'] == 'Kuv muaj 2 tug.\n\nNyob zoo.'
    assert result['timed']


@pytest.mark.parametrize('raw', [
    '00:00:02 --> 00:00:01\nHello',
    '00:00:01 --> 00:00:01\nHello',
    '00:00:60,000 --> 00:02:00,000\nHello',
    '00:60:00,000 --> 02:00:00,000\nHello',
    '00:00:1 --> 00:00:02\nHello',
    '00:00:xx --> 00:00:02\nHello',
    '00:00:01,0000 --> 00:00:02\nHello',
    '00:00:01 --> bad\nHello',
    '00:00:01 --> 00:00:02junk\nHello',
])
def test_bad_ranges_are_never_read_as_numbers_even_in_natural_mode(raw):
    for timing in ('auto', 'natural'):
        with pytest.raises(ValueError):
            parse_document(raw, timing=timing)


@pytest.mark.parametrize('second', ['00:00:02 --> 00:00:04', '00:00:00 --> 00:00:01'])
def test_overlap_or_order_rejected_for_alignment_but_cleanable_for_natural(second):
    raw = '1\n00:00:01 --> 00:00:03\nFirst 2024.\n\n2\n' + second + '\nSecond 50.'
    with pytest.raises(ValueError, match='chồng lấn'):
        parse_document(raw)
    result = parse_document(raw, timing='natural')
    assert result['text'] == 'First 2024.\n\nSecond 50.'
    assert not result['timed'] and result['warnings']


def test_touching_intervals_and_natural_mode_have_same_words():
    raw = '1\n00:00:00,000 --> 00:00:00,800\nNyob zoo.\n\n2\n00:00:00,800 --> 00:00:01,200\n123'
    assert parse_document(raw)['timed']
    result = parse_document(raw, timing='natural')
    assert not result['timed'] and result['text'] == 'Nyob zoo.\n\n123'


def test_timestamp_transcript_without_end_times_cleans_only_markers():
    raw = '[00:12.50] Kuv muaj 25 xyoo.\n[00:13][00:14] Nyob zoo 2024.\n00:20 500\n00:00:30,000\nTsis muaj mốc.'
    result = parse_document(raw)
    assert result['text'] == 'Kuv muaj 25 xyoo.\nNyob zoo 2024.\n500\n\nTsis muaj mốc.'
    assert result['format'] == 'timestamped' and not result['timed']
    assert result['duration'] is None and result['warnings']


def test_plain_text_is_not_globally_stripped_of_numbers_or_symbols():
    raw = '2024\n1. Kuv muaj 25 xyoo.\nTus nqi yog 123.45, nqe 2/3.\n3 < 5 thiab 5 > 3.\nA --> B\n1 --> 2'
    result = parse_document(raw)
    assert result['text'] == raw
    assert result['format'] == 'text' and not result['timed'] and result['cues'] == []


def test_plain_supplementary_unicode_million_characters_preserved():
    raw = '𐐀' * 1_000_000
    assert parse_document(raw)['text'] == raw
    with pytest.raises(ValueError, match='1.000.000'):
        parse_document(raw + 'x')


@pytest.mark.parametrize('raw', ['', None, ' \n ', '\ufeff00:01 --> 00:02\n', '[00:01.000]', 'WEBVTT\n\nNOTE words only'])
def test_no_spoken_content_is_reported_instead_of_synthesizing_metadata(raw):
    with pytest.raises(ValueError):
        parse_document(raw)


def test_untimed_prologue_is_not_silently_dropped():
    with pytest.raises(ValueError, match='trước mốc'):
        parse_document('Important spoken introduction\n\n1\n00:00:01 --> 00:00:02\nNyob zoo.')


def test_corrupt_huge_timeline_does_not_request_enormous_silent_audio():
    raw = '00:00:00 --> 169:00:00\nNyob zoo.'
    with pytest.raises(ValueError, match='168 giờ'):
        parse_document(raw)
    result = parse_document(raw, timing='natural')
    assert result['text'] == 'Nyob zoo.' and not result['timed']
