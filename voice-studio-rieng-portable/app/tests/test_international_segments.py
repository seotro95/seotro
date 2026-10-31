"""International packing reduces requests while preserving spoken content and barriers."""
import re

import pytest

from narration import plan_segments, split_script


def packed_job(text, **changes):
    return {'text': text, 'input_format': 'txt', 'engine': 'voxcpm',
            'segment_plan': 'international-packed-v1', 'paragraph_pause': 0,
            'language': 'ja', 'voice_id': 'selected-reference', **changes}


def spoken_content(segments):
    return re.sub(r'\s+', '', ''.join(segment.text for segment in segments))


@pytest.mark.parametrize('text,language', [
    ('こんにちは。これは最初の文です。次の文も同じ声で読みます。', 'ja'),
    ('안녕하세요. 첫 번째 문장입니다. 다음 문장도 같은 목소리로 읽습니다.', 'ko'),
    ('Bonjour. Voici la première phrase. La voix choisie reste identique.', 'fr'),
])
def test_short_international_sentences_share_one_request_without_losing_content(text, language):
    job = packed_job(text, language=language)
    original_job = job.copy()
    classic = split_script(text)
    packed = plan_segments(job)
    assert len(classic) == 3 and len(packed) == 1
    assert spoken_content(packed) == spoken_content(classic)
    assert all(len(segment.text) <= 240 for segment in packed)
    assert job == original_job


def test_packing_retains_explicit_pauses_and_emphasis_boundaries():
    text = 'Bonjour. Bienvenue.[pause=1.25]Une phrase. Encore une.**Attention. Important.**La fin. Merci.'
    packed = plan_segments(packed_job(text, language='fr'))
    assert [(s.text, s.pause, s.emphasis) for s in packed] == [
        ('Bonjour. Bienvenue.', 0, False),
        ('', 1.25, False),
        ('Une phrase. Encore une.', 0, False),
        ('Attention.', 0, True),
        ('Important.', 0, True),
        ('La fin. Merci.', 0, False),
    ]
    assert spoken_content(packed) == spoken_content(split_script(text))


def test_zero_second_explicit_pause_still_separates_model_requests():
    packed = plan_segments(packed_job('最初の文。[pause=0]次の文。'))
    assert [segment.text for segment in packed] == ['最初の文。', '', '次の文。']


@pytest.mark.parametrize('changes', [
    {'segment_plan': 'classic-v1'},
    {'segment_plan': None},
    {'paragraph_pause': .5},
    {'paragraph_pause': None},
    {'engine': 'vieneu'},
    {'engine': 'vieneu_nano'},
])
def test_old_jobs_and_nonzero_gaps_keep_the_classic_plan(changes):
    text = 'First sentence. Second sentence. Third sentence.'
    assert plan_segments(packed_job(text, **changes)) == split_script(text)


def test_srt_cues_keep_the_same_segments_and_order():
    text = ('1\n00:00:00,500 --> 00:00:02,500\nこんにちは。最初の文です。\n\n'
            '2\n00:00:04,000 --> 00:00:06,000\n次の文です。最後の文です。')
    job = packed_job(text, input_format='srt')
    packed = plan_segments(job)
    assert packed == plan_segments({**job, 'segment_plan': 'classic-v1'})
    assert [segment.cue for segment in packed] == [0, 0, 1, 1]


@pytest.mark.parametrize('text', [
    ' '.join(f'word{index}.' for index in range(150)),
    '同じ声で次の短い文を読みます。' * 100,
    '같은 목소리로 다음 문장을 읽습니다. ' * 100,
])
def test_long_text_is_bounded_without_dropping_or_reordering_words(text):
    packed = plan_segments(packed_job(text))
    classic = split_script(text)
    assert len(packed) < len(classic)
    assert all(0 < len(segment.text) <= 240 for segment in packed)
    assert spoken_content(packed) == re.sub(r'\s+', '', text)
