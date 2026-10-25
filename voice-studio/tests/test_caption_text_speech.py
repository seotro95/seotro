"""TXT captions lose metadata, never the speaker's numbers or RPA words."""
import importlib
import wave

import pytest

from narration import plan_segments, spoken_text
from subtitles import parse_srt


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
@pytest.mark.parametrize('skip', [True, False])
def test_pasted_captions_ignore_metadata_even_when_single_labels_are_opted_out(newline, skip):
    source = ('\ufeff7\n\n"00:04:28,533 --> 00:04:29,333"\n'
              '<b>Kuv muaj 12 tug me nyuam.</b>\n8\n'
              '\u200b99:59.500 → 100:00.300 align:start position:0% Ua tsaug.').replace('\n', newline)
    parts = plan_segments({'text': source, 'input_format': 'txt', 'skip_timestamps': skip})
    assert ' '.join(part.text for part in parts) == 'Kuv muaj 12 tug me nyuam. Ua tsaug.'


@pytest.mark.parametrize('timing', [
    '[00:04:28,533] --> [00:04:29,333]',
    '“00:04:28,533 --> 00:04:29,333”',
    '7) 04:28.533 -> 04:29.333',
    '(04:28.533 -->04:29.333)',
])
def test_wrapped_clocks_and_inline_words_do_not_lose_content(timing):
    assert spoken_text(timing + ' <b>Pab paj pav pas pag pam pad pa; 42.</b>').strip() == 'Pab paj pav pas pag pam pad pa; 42.'


@pytest.mark.parametrize('parser', [spoken_text, parse_srt])
def test_number_before_an_unindexed_following_cue_stays_spoken(parser):
    source = ('00:00:01,000 -->00:00:02,000\nKuv nyob xyoo\n2025\n'
              '00:00:02,000 -->00:00:03,000\nUa tsaug.')
    result = parser(source)
    words = result if isinstance(result, str) else '\n'.join(cue['text'] for cue in result)
    assert '2025' in words and 'Ua tsaug.' in words


def test_numeric_body_survives_before_next_numbered_cue():
    source = ('1\n00:00:01,000 -->00:00:02,000\n42\n'
              '2\n00:00:02,000 -->00:00:03,000\nUa tsaug.')
    assert [cue['text'] for cue in parse_srt(source)] == ['42', 'Ua tsaug.']
    assert spoken_text(source).split() == ['42', 'Ua', 'tsaug.']


def test_txt_worker_reads_only_words_without_padding_to_caption_clocks(tmp_path, monkeypatch):
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
            audio.writeframes(b'\x00\x20' * 12000)

    source = ('1\n00:04:28,533 -->00:04:29,333\nKuv muaj 12 tug.\n'
              '2\n99:59.500 -->100:00.300\nUa tsaug.')
    worker.render({'id': 'caption-txt', 'text': source, 'input_format': 'txt',
                   'engine': 'vieneu', 'format': 'wav', 'speed': 1,
                   'paragraph_pause': 0}, synthesize)
    assert received == ['Kuv muaj 12 tug.', 'Ua tsaug.']
    with wave.open(str(tmp_path / 'audio/caption-txt.wav')) as audio:
        assert audio.getnframes() == 24000
    assert [cue['text'] for cue in parse_srt((tmp_path / 'audio/caption-txt.srt').read_text())] == received


@pytest.mark.parametrize('source', [
    '00:04:28,533 -->broken\nNyob zoo.',
    '00:04:28,533 -->\nNyob zoo.',
    '00:04:60,000 -->00:04:61,000\nNyob zoo.',
])
def test_malformed_range_is_actionable_error_instead_of_spoken_numbers(source):
    with pytest.raises(ValueError, match='Mốc|mốc'):
        spoken_text(source)
