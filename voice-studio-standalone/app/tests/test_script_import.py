"""Real script file bytes and timeline parsing, independent of speech models."""
import pytest

from script_import import (MAX_FILE_BYTES, decode_script_bytes,
                           import_script_bytes, parse_script_text)
from subtitles import export_srt, parse_clock, parse_srt


@pytest.mark.parametrize('codec,bom', [
    ('utf-8', b''), ('utf-8', b'\xef\xbb\xbf'),
    ('utf-16-le', b'\xff\xfe'), ('utf-16-be', b'\xfe\xff'),
    ('utf-16-le', b''), ('utf-16-be', b''),
    ('utf-32-le', b'\xff\xfe\x00\x00'), ('utf-32-be', b'\x00\x00\xfe\xff'),
])
def test_windows_file_encodings_and_crlf_keep_vietnamese_and_exact_times(codec, bom):
    source = '1\r\n00:00:01,025 --> 00:00:03,875\r\nTiếng Việt: một lời chào.\r\n'
    result = import_script_bytes(bom + source.encode(codec), 'LOI THOAI.SRT')
    assert result['cues'] == [{'start': 1.025, 'end': 3.875, 'text': 'Tiếng Việt: một lời chào.'}]
    assert result['has_timeline'] is True
    assert result['timeline_seconds'] == 3.875
    assert result['requires_total_duration'] is False
    assert parse_srt(result['text']) == result['cues']
    assert result['source_text'] == source.replace('\r\n', '\n')
    assert result['source_input_format'] == 'srt'


def test_legacy_windows_vietnamese_tone_marks_normalize_without_replacement():
    source = 'Tiếng Việt: một lời chào.'
    result = import_script_bytes(source.encode('cp1258'), 'noi-dung.txt')
    assert result['text'] == 'Tiếng Việt: một lời chào.'
    assert result['encoding'] == 'Windows-1258'
    assert result['warnings']
    assert result['has_timeline'] is False


@pytest.mark.parametrize('payload', [
    b'\xff\xfe\x00', b'\x81\x8d', b'\x00\x01\x00\x02\x00\x03',
    'Lỗi � ký tự'.encode('utf-8'), b'hello\x01world',
])
def test_unreadable_or_binary_files_fail_instead_of_losing_characters(payload):
    with pytest.raises(ValueError):
        import_script_bytes(payload, 'bad.txt')


def test_file_import_limits_and_extension_are_checked_before_parsing():
    with pytest.raises(ValueError, match='2 MB'):
        decode_script_bytes(b'x' * (MAX_FILE_BYTES + 1))
    with pytest.raises(ValueError, match='200.000'):
        import_script_bytes(('a' * 200_001).encode(), 'large.txt')
    with pytest.raises(ValueError, match='đuôi'):
        import_script_bytes(b'text', 'text.pdf')
    with pytest.raises(ValueError, match='nội dung'):
        import_script_bytes(b'\xef\xbb\xbf\r\n', 'empty.txt')


def test_plain_txt_preserves_numbers_inside_dialogue_without_inventing_duration():
    result = import_script_bytes('Hẹn lúc 12:30. Tôi có 25 phút để nói.\rXin chào.'.encode(), 'script.txt')
    assert result['text'] == 'Hẹn lúc 12:30. Tôi có 25 phút để nói.\nXin chào.'
    assert result['input_format'] == 'txt'
    assert result['timeline_seconds'] is None
    assert result['has_timeline'] is False


@pytest.mark.parametrize('source', [
    '[00:01,025 - 00:03,875] Xin chào.\n[00:05 - 00:07.250] Tạm biệt.',
    '(00:01.025–00:03.875) Xin chào.\n(00:05–00:07.250) Tạm biệt.',
    '00:01.025 --> 00:03.875 Xin chào.\n00:05 → 00:07.250 Tạm biệt.',
    '[00:00:01,025 --> 00:00:03,875] Xin chào.\n[00:00:05,000 --> 00:00:07,250] Tạm biệt.',
    '[00:01.025 - 00:03.875]\nXin chào.\n[00:05 - 00:07.250]\nTạm biệt.',
])
def test_timed_txt_ranges_become_srt_with_gaps_preserved(source):
    result = parse_script_text(source)
    assert result['input_format'] == 'srt'
    assert result['timeline_seconds'] == 7.25
    assert result['cues'] == [
        {'start': 1.025, 'end': 3.875, 'text': 'Xin chào.'},
        {'start': 5.0, 'end': 7.25, 'text': 'Tạm biệt.'},
    ]
    assert parse_srt(result['text']) == result['cues']


def test_start_only_txt_requires_real_final_duration_then_uses_next_start_for_each_cue():
    source = '[00:01] Xin chào.\n00:03 Tạm biệt.\nDòng thoại tiếp theo.'
    pending = parse_script_text(source)
    assert pending['requires_total_duration'] is True
    assert pending['timeline_seconds'] is None
    assert pending['text'] == source
    assert pending['cues'][-1]['end'] is None
    result = parse_script_text(source, total_seconds=6.125)
    assert result['requires_total_duration'] is False
    assert result['cues'] == [
        {'start': 1.0, 'end': 3.0, 'text': 'Xin chào.'},
        {'start': 3.0, 'end': 6.125, 'text': 'Tạm biệt.\nDòng thoại tiếp theo.'},
    ]
    assert result['timeline_seconds'] == 6.125


def test_mixed_start_only_and_explicit_ranges_keep_all_dialogue():
    result = parse_script_text('00:00 Bắt đầu.\n00:02 --> 00:04 Câu giữa.\n[00:05] Câu cuối.', total_seconds=7)
    assert [(cue['start'], cue['end']) for cue in result['cues']] == [(0, 2), (2, 4), (5, 7)]
    assert [cue['text'] for cue in result['cues']] == ['Bắt đầu.', 'Câu giữa.', 'Câu cuối.']


@pytest.mark.parametrize('source,kwargs', [
    ('[00:03 - 00:02] Đảo mốc.', {}),
    ('[00:00 - 00:03] Một.\n[00:02 - 00:04] Hai.', {}),
    ('[00:00 - 00:03] Một.\n[00:02] Hai.', {}),
    ('[00:02] Một.\n[00:02] Hai.', {}),
    ('[00:03] Một.', {'total_seconds': 2}),
    ('[00:00] Thiếu kết thúc.', {'total_seconds': float('nan')}),
    ('[00:00] Thiếu kết thúc.', {'total_seconds': 2.0001}),
    ('[00:00] Thiếu kết thúc.', {'total_seconds': True}),
    ('Lời chưa có mốc.\n[00:02 - 00:05] Lời có mốc.', {}),
    ('[00:00 - 00:02] Một.\n[00:99] Sai phút.', {}),
    ('[00:00 - 00:02]\n[00:03 - 00:05] Hai.', {}),
])
def test_ambiguous_invalid_and_overlapping_txt_timelines_are_never_silently_fixed(source, kwargs):
    with pytest.raises(ValueError):
        parse_script_text(source, **kwargs)


def test_srt_variants_without_blank_lines_round_trip_millisecond_precision():
    source = '\ufeff1\r00:01.025 --> 00:02.5\r<i>Xin chào.</i>\r2\r00:03 → 00:05\r<An> &amp; bạn.'
    result = import_script_bytes(source.encode('utf-16'), 'sub.srt')
    assert result['cues'] == [
        {'start': 1.025, 'end': 2.5, 'text': 'Xin chào.'},
        {'start': 3.0, 'end': 5.0, 'text': '<An> & bạn.'},
    ]
    assert parse_srt(export_srt(result['cues'])) == result['cues']


def test_srt_saved_as_txt_keeps_timeline_and_dialogue_instead_of_reading_indexes():
    source = '1\n00:00:00,000 --> 00:00:02,000\nXin chào.\n\n2\n00:00:03,000 --> 00:00:04,000\nTạm biệt.'
    result = import_script_bytes(source.encode(), 'caption.txt')
    assert result['input_format'] == 'srt'
    assert result['timeline_seconds'] == 4
    assert [cue['text'] for cue in result['cues']] == ['Xin chào.', 'Tạm biệt.']


@pytest.mark.parametrize('source', [
    '1\n00:00:00,000 --> 00:00:03,000\nMột.\n\n2\n00:99:00,000 --> 00:99:02,000\nHai.',
    '1\n00:00:00,000 --> 00:00:03,000\nMột.\n\n2\n00:02:00,000 --> 00:02:02,000\n',
    '1\n00:00:00,000 --> 00:00:03,000\nMột.\n\n2\n00:00:02,000 --> 00:00:04,000\nHai.',
])
def test_bad_srt_does_not_read_malformed_clocks_or_skip_empty_cues(source):
    with pytest.raises(ValueError, match='^SRT:'):
        parse_srt(source)


def test_clock_and_srt_export_boundary_at_three_hours():
    assert parse_clock('180:00') == parse_clock('03:00:00,000') == 10800
    with pytest.raises(ValueError):
        parse_clock('03:00:00,001')


def test_final_pending_start_must_itself_be_inside_timeline_limit():
    with pytest.raises(ValueError, match='3 giờ'):
        parse_script_text('[03:00:01] Câu cuối chưa có mốc kết thúc.')
    with pytest.raises(ValueError, match='3 giờ'):
        parse_script_text('[03:00:00] Không còn thời gian cho lời đọc.')


def test_repeated_srt_canonicalization_never_loses_literal_html_or_ampersands():
    source = '1\n00:00:00,000 --> 00:00:02,000\nNói &lt;i&gt;một từ&lt;/i&gt;, &amp;amp;, &lt;An&gt;.'
    expected = 'Nói <i>một từ</i>, &amp;, <An>.'
    for _ in range(4):
        cues = parse_srt(source)
        assert cues[0]['text'] == expected
        source = export_srt(cues)


def test_large_valid_source_keeps_original_when_canonical_timing_overhead_grows():
    source = '\n'.join(f'[{index // 60:02}:{index % 60:02}-{(index + 1) // 60:02}:{(index + 1) % 60:02}] x' for index in range(9000))
    assert len(source) <= 200_000
    result = parse_script_text(source)
    assert len(result['text']) > 200_000
    assert result['source_text'] == source
    assert result['source_input_format'] == 'txt'
    assert len(result['cues']) == 9000
