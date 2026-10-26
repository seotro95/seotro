"""Hmong packing preserves text and narration controls before F5 inference."""
import pytest

from narration import plan_segments, validate_voice_text


def hmong_job(text, **options):
    return {'text': text, 'engine': 'f5_hmong', 'paragraph_pause': 0,
            'segment_plan': 'hmong-packed-v1', **options}


def test_adjacent_sentences_pack_without_losing_punctuation_or_rpa_tones():
    text = 'Nyob zoo. Pab paj pav pas pag pam pad pa!\nUa tsaug.'
    segments = plan_segments(hmong_job(text))
    assert len(segments) == 1
    assert segments[0].text == text.replace('\n', ' ')
    assert all(len(segment.text) <= 160 for segment in segments)


def test_positive_pause_and_legacy_jobs_keep_separate_sentences():
    text = 'Nyob zoo. Ua tsaug.'
    assert [segment.text for segment in plan_segments(hmong_job(text, paragraph_pause=.3))] == ['Nyob zoo.', 'Ua tsaug.']
    assert [segment.text for segment in plan_segments(hmong_job(text, segment_plan='classic-v1'))] == ['Nyob zoo.', 'Ua tsaug.']
    assert len(plan_segments({'text': text, 'engine': 'f5_hmong', 'paragraph_pause': 0})) == 2


def test_explicit_zero_pause_and_emphasis_remain_packing_barriers():
    text = 'Nyob zoo. Ua tsaug. **Pab paj.** Kuv tuaj. [pause=0] Peb nyob nov.'
    segments = plan_segments(hmong_job(text))
    assert [(segment.text, segment.pause, segment.emphasis) for segment in segments] == [
        ('Nyob zoo. Ua tsaug.', 0, False), ('Pab paj.', 0, True),
        ('Kuv tuaj.', 0, False), ('', 0, False), ('Peb nyob nov.', 0, False)]


def test_unicode_formatting_normalizes_only_spoken_content_after_control_parsing():
    segments = plan_segments(hmong_job('“Nyob\u00a0zoo…” **Pab—paj.** [pause=1.5]\nUa tsaug.'))
    assert [(segment.text, segment.pause, segment.emphasis) for segment in segments] == [
        ('Nyob zoo...', 0, False), ('Pab-paj.', 0, True),
        ('', 1.5, False), ('Ua tsaug.', 0, False)]
    with pytest.raises(ValueError, match='RPA'):
        plan_segments(hmong_job('Nyob zoo. **你好** [pause=1] Ua tsaug.'))
    with pytest.raises(ValueError, match='Lời mẫu tham chiếu.*RPA'):
        validate_voice_text('Tiếng Việt', 'f5_hmong', 'Lời mẫu tham chiếu')


def test_long_text_stays_bounded_and_never_splits_a_tone_suffix():
    text = ' '.join(['Pab paj pav pas pag pam pad pa.'] * 30)
    segments = plan_segments(hmong_job(text))
    assert len(segments) > 1
    assert all(len(segment.text) <= 160 for segment in segments)
    assert ' '.join(segment.text for segment in segments) == text
    with pytest.raises(ValueError, match='không tự cắt chữ ghi thanh điệu'):
        plan_segments(hmong_job('P' * 161))


def test_srt_packing_stays_within_each_cue():
    text = '1\n00:00:00,000 --> 00:00:05,000\nNyob zoo. Ua tsaug.\n\n2\n00:00:05,000 --> 00:00:10,000\nKuv tuaj. Peb nyob nov.\n'
    segments = plan_segments(hmong_job(text, input_format='srt'))
    assert [(segment.cue, segment.text) for segment in segments] == [
        (0, 'Nyob zoo. Ua tsaug.'), (1, 'Kuv tuaj. Peb nyob nov.')]
