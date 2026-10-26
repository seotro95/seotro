"""Retain Hmong linguistic context without pretending to align individual words."""
from dataclasses import asdict

import pytest

from hmong_text import normalize_text
from narration import plan_segments


def job(text, **changes):
    return {'engine': 'f5_hmong', 'segment_plan': 'hmong-expression-v1',
            'hmong_phrase_context': True, 'text': text, 'input_format': 'txt',
            'emotion': 'warm', 'emotion_strength': .65, 'auto_rhythm': True,
            'paragraph_pause': 0, **changes}


def spoken(segments):
    return [segment for segment in segments if segment.text]


WORDS = 'Peb **ua** hauj lwm. Thaj chaw no zoo nkauj. Nyob qab roob. Peb faib mov. Kuv rov los tsev. Nws hnav ris.'
PLAIN = WORDS.replace('**', '')


def test_emphasized_word_keeps_its_complete_sentence_and_rpa_words():
    segments = spoken(plan_segments(job(WORDS)))
    assert [segment.text for segment in segments] == [
        'Peb ua hauj lwm.', 'Thaj chaw no zoo nkauj.', 'Nyob qab roob.',
        'Peb faib mov.', 'Kuv rov los tsev.', 'Nws hnav ris.']
    assert [segment.emphasis for segment in segments] == [True, False, False, False, False, False]
    assert ' '.join(segment.text for segment in segments) == PLAIN
    assert all('**' not in segment.text and '[' not in segment.text for segment in segments)
    assert all(segment.rhythm_pause > 0 for segment in segments)


def test_rhythm_off_packs_context_including_emphasis_in_one_bounded_model_call():
    contextual = spoken(plan_segments(job(WORDS, auto_rhythm=False)))
    legacy = spoken(plan_segments(job(WORDS, auto_rhythm=False, hmong_phrase_context=False)))
    assert len(contextual) == 1 < len(legacy)
    assert contextual[0].text == PLAIN
    assert contextual[0].emphasis and contextual[0].rhythm_pause == 0


def test_reported_words_keep_exact_letters_case_and_tone_suffixes():
    source = 'ua **thaj** qab faib rov ris.'
    segments = spoken(plan_segments(job(source)))
    assert len(segments) == 1 and segments[0].text == 'ua thaj qab faib rov ris.'
    assert segments[0].emphasis


@pytest.mark.parametrize('text', ['Nyo**b** zoo.', '**Nyo**b zoo.', 'Nyob zo**o**.'])
def test_bold_inside_rpa_word_is_rejected_without_splitting_tone_letters(text):
    with pytest.raises(ValueError, match='bên trong âm tiết RPA'):
        plan_segments(job(text))


def test_emphasis_can_cross_sentences_without_breaking_them_into_bold_fragments():
    segments = spoken(plan_segments(job('Peb **ua hauj lwm. Thaj** chaw no zoo nkauj.')))
    assert [segment.text for segment in segments] == ['Peb ua hauj lwm.', 'Thaj chaw no zoo nkauj.']
    assert all(segment.emphasis for segment in segments)


def test_bold_punctuation_does_not_mark_unrelated_spoken_words():
    segments = spoken(plan_segments(job('Peb ua hauj lwm**.**')))
    assert len(segments) == 1 and segments[0].text == 'Peb ua hauj lwm.'
    assert not segments[0].emphasis


def test_zero_pause_is_a_real_boundary_and_overrides_automatic_gap():
    segments = plan_segments(job('Peb **ua** hauj lwm.[pause=0]Kuv rov los tsev.', auto_rhythm=False))
    assert len(segments) == 3
    assert segments[0].text == 'Peb ua hauj lwm.' and segments[0].emphasis
    assert segments[0].rhythm_pause == 0
    assert not segments[1].text and segments[1].pause == 0
    assert segments[2].text == 'Kuv rov los tsev.' and not segments[2].emphasis
    rhythmic = plan_segments(job('Peb ua hauj lwm.[pause=0]Kuv rov los tsev.'))
    assert rhythmic[0].rhythm_pause == 0 < rhythmic[2].rhythm_pause


def test_emotion_barriers_keep_complete_context_and_no_controls_reach_model():
    segments = spoken(plan_segments(job(
        'Peb **ua** hauj lwm.[emotion=serious]Thaj chaw no zoo nkauj. '
        '[emotion=warm]Nyob qab roob.', auto_rhythm=False)))
    assert [(segment.text, segment.emotion) for segment in segments] == [
        ('Peb ua hauj lwm.', 'warm'), ('Thaj chaw no zoo nkauj.', 'serious'), ('Nyob qab roob.', 'warm')]
    assert [segment.emphasis for segment in segments] == [True, False, False]


def test_cue_boundaries_and_emotion_reset_preserve_whole_cue_context():
    source = ('1\n00:00:00,000 --> 00:00:05,000\n'
              '[emotion=serious]Peb **ua** hauj lwm. Thaj chaw no zoo nkauj.\n\n'
              '2\n00:00:06,000 --> 00:00:10,000\nKuv rov los tsev. Nws hnav ris.\n')
    segments = spoken(plan_segments(job(source, input_format='srt')))
    assert [(segment.text, segment.cue, segment.emotion) for segment in segments] == [
        ('Peb ua hauj lwm. Thaj chaw no zoo nkauj.', 0, 'serious'),
        ('Kuv rov los tsev. Nws hnav ris.', 1, 'warm')]
    assert segments[0].emphasis and not segments[1].emphasis
    assert all(segment.rhythm_pause == 0 for segment in segments)


def test_bounds_keep_whole_rpa_words_and_only_mark_the_containing_piece():
    text = ('Nyob zoo. ' * 19) + '**ua** hauj lwm. ' + ('Kuv rov los tsev. ' * 15)
    normalized = normalize_text(text.replace('**', ''))
    segments = spoken(plan_segments(job(text, auto_rhythm=False)))
    assert len(segments) > 2
    assert all(0 < len(segment.text) <= 160 for segment in segments)
    assert ' '.join(segment.text for segment in segments) == normalized
    marked = [segment for segment in segments if segment.emphasis]
    assert len(marked) == 1 and 'ua hauj lwm.' in marked[0].text
    with pytest.raises(ValueError, match='không tự cắt chữ ghi thanh điệu'):
        plan_segments(job('a' * 161))


def test_normalization_keeps_tone_letters_across_quotes_and_paragraphs():
    source = '“Peb **ua** hauj lwm…”\nThaj\u00a0chaw no zoo nkauj.\n\nKuv rov los tsev.'
    segments = spoken(plan_segments(job(source)))
    assert [segment.text for segment in segments] == [
        'Peb ua hauj lwm...', 'Thaj chaw no zoo nkauj.', 'Kuv rov los tsev.']
    assert segments[0].emphasis and all(segment.rhythm_pause > 0 for segment in segments)
    assert all(segment.emotion == 'warm' for segment in segments)


@pytest.mark.parametrize('source', [
    '[emotion=angry]Peb ua hauj lwm.', '[emotion=warm Peb ua hauj lwm.',
    'Peb **ua hauj lwm.', '[pause=-1]Nyob zoo.', '[pause=11]Nyob zoo.',
    '[pause]Nyob zoo.', 'Nyob zoo. [emotion', 'Peb ***ua*** hauj lwm.',
])
def test_malformed_controls_raise_actionable_errors(source):
    with pytest.raises(ValueError):
        plan_segments(job(source))


def test_legacy_v1_jobs_keep_their_exact_saved_plan_when_flag_is_absent_or_false():
    source = 'Peb **ua** hauj lwm.[pause=0][emotion=serious]Kuv rov los tsev.'
    explicit_old = job(source, hmong_phrase_context=False)
    saved_old = dict(explicit_old)
    saved_old.pop('hmong_phrase_context')
    planned = [asdict(segment) for segment in plan_segments(explicit_old)]
    assert [asdict(segment) for segment in plan_segments(saved_old)] == planned
    assert [item['text'] for item in planned] == ['Peb', 'ua', 'hauj lwm.', '', 'Kuv rov los tsev.']
    assert [item['emphasis'] for item in planned] == [False, True, False, False, False]


def test_context_flag_does_not_change_non_hmong_or_other_saved_segment_plans():
    source = 'Peb **ua** hauj lwm.'
    for changes in ({'engine': 'system'}, {'segment_plan': 'hmong-packed-v1'}):
        contextual = job(source, **changes)
        old = {**contextual, 'hmong_phrase_context': False}
        assert [asdict(segment) for segment in plan_segments(contextual)] == [
            asdict(segment) for segment in plan_segments(old)]
