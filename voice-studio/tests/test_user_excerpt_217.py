"""Only the spoken Hmong line survives the user's numbered caption excerpt."""
import pytest

from narration import spoken_text
from subtitles import parse_srt

WORDS = 'Tae-yong cov ntaub ntawv tus kheej'
TIMING = '00:06:07,200 --> 00:06:08,400'


@pytest.mark.parametrize('source', [
    f'217\n{TIMING}\n{WORDS}',
    f'"217\n{TIMING}\n{WORDS} "',
    f'“217\n{TIMING}\n{WORDS}”',
    f'"217"\n{TIMING}\n{WORDS}',
    f'[217]\n{TIMING}\n{WORDS}',
    f'"{TIMING}\n{WORDS}"',
])
@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
def test_user_excerpt_217_has_no_narrated_index_or_clocks(source, newline):
    source = source.replace('\n', newline)
    assert spoken_text(source).strip() == WORDS
    assert parse_srt(source) == [{'start': 367.2, 'end': 368.4, 'text': WORDS}]


@pytest.mark.parametrize('separator', ['\n', '\n\n'])
@pytest.mark.parametrize('last_index', ['219', '217', '1', '"219"'])
def test_cropped_numbered_subtitles_can_skip_or_restart_indices(separator, last_index):
    source = f'217\n{TIMING}\n{WORDS}{separator}{last_index}\n00:06:09,000 -->00:06:12,000\nKuv muaj 12 tug.'
    assert [cue['text'] for cue in parse_srt(source)] == [WORDS, 'Kuv muaj 12 tug.']
    assert ' '.join(spoken_text(source).split()) == WORDS + ' Kuv muaj 12 tug.'


def test_actual_numeric_body_and_quoted_dialogue_stay_spoken():
    source = f'217\n{TIMING}\n42\n219\n00:06:09,000 -->00:06:12,000\n"Nyob zoo", kuv muaj 12 tug.'
    assert [cue['text'] for cue in parse_srt(source)] == ['42', '"Nyob zoo", kuv muaj 12 tug.']
    assert spoken_text('"Nyob zoo", kuv muaj 12 tug.').strip() == '"Nyob zoo", kuv muaj 12 tug.'


def test_zero_based_ordinal_is_metadata_only_before_a_clock_range():
    source = f'0\n{TIMING}\n{WORDS}'
    assert spoken_text(source).strip() == WORDS
    assert parse_srt(source)[0]['text'] == WORDS
