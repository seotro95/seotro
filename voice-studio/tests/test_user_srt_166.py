"""Preserve the exact four-cue Hmong file and identify actual timing errors."""
import pytest

from caption_markers import clean_caption_markup
from narration import plan_segments, spoken_text
from subtitles import export_srt, parse_srt


WORDS = [
    'Tus txiv neej taub hau do nqa ib tog ntoo hnyav tsib caug kilo ntaus rau daim iav kawg zog',
    'Tab sis daim iav muaj zog ntawd tseem tsis tawg li',
    'Thaum Win pom lo lus Made in China sau rau saum daim iav',
    'Nws thiaj xav tsis thoob kiag',
]
TIMES = [(.133, 3.066), (3.5, 5.166), (5.533, 8), (8.266, 9)]
SOURCE = ('1\n00:00:00,133 --> 00:00:03,066\n' + WORDS[0]
          + '\n\n2\n00:00:03,500 --> 00:00:05,166\n' + WORDS[1]
          + '\n\n3\n00:00:05,533 --> 00:00:08,000\n' + WORDS[2]
          + '\n\n4\n00:00:08,266 --> 00:00:09,000\n' + WORDS[3])


@pytest.mark.parametrize('newline', ['\n', '\r\n', '\r'])
@pytest.mark.parametrize('wrapper', [('', ''), ('"', '"'), ('“', '”'), ('(', ')'), ('[', ']')])
def test_exact_user_file_keeps_all_words_and_millisecond_cues(newline, wrapper):
    source = wrapper[0] + SOURCE.replace('\n', newline) + wrapper[1]
    expected = [dict(start=start, end=end, text=text) for (start, end), text in zip(TIMES, WORDS)]
    parsed = parse_srt(source)
    assert parsed == expected
    assert parse_srt(export_srt(parsed)) == expected
    assert ' '.join(spoken_text(source).split()) == ' '.join(WORDS)
    parts = plan_segments({'text': source, 'input_format': 'srt',
        'engine': 'hmong_native', 'segment_plan': 'hmong-expression-v1',
        'subtitle_timing': True, 'hmong_phrase_context': True,
        'auto_rhythm': False, 'paragraph_pause': 0})
    assert [(part.cue, part.text) for part in parts] == list(enumerate(WORDS))


@pytest.mark.parametrize('words', [
    '"Nyob zoo", nws hais tias (rov los tsev).',
    'Peb muaj tsib < kaum > peb tug.',
    'Nws hu <Tae-yong> thiab <Made in China>.',
    'Peb hais &lt;Nyob zoo&gt; rau koj.',
])
def test_quoted_parenthetical_and_literal_angle_words_are_not_erased(words):
    expected = words.replace('&lt;', '<').replace('&gt;', '>')
    source = '1\n00:00:00,000 -->00:00:03,000\n' + words
    assert parse_srt(source)[0]['text'] == expected
    assert clean_caption_markup(words) == expected


def test_actual_caption_styling_and_line_breaks_do_not_become_spoken_tags():
    source = '<b>Nyob zoo</b><br/><i>(Ua tsaug)</i> <font color="#fff">koj</font> <c.green>mloog</c>'
    assert clean_caption_markup(source) == 'Nyob zoo\n(Ua tsaug) koj mloog'
    assert parse_srt('00:00:00,000 -->00:00:03,000\n' + source)[0]['text'] == 'Nyob zoo\n(Ua tsaug) koj mloog'


@pytest.mark.parametrize('tail,reason,clock', [
    ('00:00:02,000 -->00:00:04,000\nUa tsaug.', 'chồng lên câu 1', '00:00:02,000'),
    ('00:00:04,000 -->00:00:03,000\nUa tsaug.', 'mốc kết thúc phải lớn hơn', '00:00:04,000'),
    ('00:00:04,000 -->00:00:05,000\n<b></b>', 'chưa có lời đọc', '00:00:04,000'),
    ('03:00:00,000 -->03:00:00,001\nUa tsaug.', 'vượt giới hạn 3 giờ', '03:00:00,001'),
])
def test_actual_invalid_cue_is_identified_without_false_generic_diagnosis(tail, reason, clock):
    source = '1\n00:00:00,000 -->00:00:03,000\nNyob zoo.\n\n2\n' + tail
    with pytest.raises(ValueError) as error:
        parse_srt(source)
    assert 'SRT: câu 2' in str(error.value)
    assert reason in str(error.value) and clock in str(error.value)
    assert 'cần lời đọc, mốc tăng dần' not in str(error.value)
