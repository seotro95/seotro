"""Only target-speech numerals become words; source/RPA spelling survives."""
import pytest

from hmong_native import EngineError, validate_text
from hmong_text import HmongTextError, normalize_speech_text, normalize_text
from narration import plan_segments


@pytest.mark.parametrize('digits,words', [
    ('0', 'xoom'), ('2', 'ob'), ('10', 'kaum'), ('12', 'kaum ob'),
    ('20', 'nees nkaum'), ('28', 'nees nkaum yim'), ('30', 'peb caug'),
    ('99', 'cuaj caug cuaj'), ('100', 'ib puas'), ('101', 'ib puas ib'),
    ('120', 'ib puas nees nkaum'), ('1000', 'ib txhiab'),
    ('2026', 'ob txhiab nees nkaum rau'), ('200000', 'ob puas txhiab'),
    ('1000000', 'ib lab'), ('123456789', 'ib puas nees nkaum peb lab plaub puas tsib caug rau txhiab xya puas yim caug cuaj'),
])
def test_cardinal_counts_are_hmong_words_before_native_vocabulary_validation(digits, words):
    source = f'Kuv muaj {digits} tug.'
    spoken = f'Kuv muaj {words} tug.'
    assert normalize_text(source) == source
    assert normalize_speech_text(source) == spoken
    assert normalize_speech_text(spoken) == spoken
    assert validate_text(source) == spoken.lower()


@pytest.mark.parametrize('source,spoken', [
    ('200.000', 'ob puas txhiab'),
    ('200,000', 'ob puas txhiab'),
    ('1,234,567', 'ib lab ob puas peb caug plaub txhiab tsib puas rau caug xya'),
    ('12.05', 'kaum ob. xoom tsib'),
    ('12,05', 'kaum ob, xoom tsib'),
    ('1,234.50', 'ib txhiab ob puas peb caug plaub. tsib xoom'),
    ('1.234,50', 'ib txhiab ob puas peb caug plaub, tsib xoom'),
    ('007', 'xoom xoom xya'),
    ('1234567890', 'ib ob peb plaub tsib rau xya yim cuaj xoom'),
])
def test_number_format_rules_do_not_drop_significant_digits(source, spoken):
    assert normalize_speech_text(source) == spoken
    assert not any(character.isdigit() for character in validate_text(source))


def test_existing_words_case_rpa_tone_letters_and_prose_time_survive():
    source = 'UA thaj QAB faib ROV ris. POB POJ POS POV POM POG POD PO. Kuv tuaj thaum 12:30.'
    assert normalize_speech_text(source) == source.replace('12:30', 'kaum ob:peb caug')


@pytest.mark.parametrize('source', ['ua2', '12abc', 'v1.2', '192.168.0.1', 'https://example.com/12'])
def test_codes_urls_and_malformed_numbers_are_not_guessed(source):
    assert normalize_speech_text(source) == source
    with pytest.raises(EngineError):
        validate_text(source)


@pytest.mark.parametrize('source', ['-12', '+12', 'Kuv muaj -12 tug.', '(-12)'])
def test_signed_counts_are_explicitly_rejected_instead_of_losing_the_sign(source, monkeypatch):
    from hmong_engine import SpeechEngine

    with pytest.raises(HmongTextError, match='số có dấu'):
        normalize_speech_text(source)
    with pytest.raises(EngineError, match='số có dấu'):
        validate_text(source)
    engine = SpeechEngine()
    monkeypatch.setattr(engine, '_load', lambda quality: pytest.fail('Invalid number must not load weights'))
    with pytest.raises(EngineError, match='số có dấu'):
        engine.synthesize(source, '/missing/reference.wav', 'Nyob zoo.')


def test_numeric_range_retains_its_written_boundary():
    assert normalize_speech_text('12-15') == 'kaum ob-kaum tsib'


@pytest.mark.parametrize('engine', ['hmong_native', 'f5_hmong'])
@pytest.mark.parametrize('plan,context', [(None, False), ('hmong-packed-v1', False),
                                        ('hmong-expression-v1', False), ('hmong-expression-v1', True)])
def test_every_target_planner_speaks_number_after_removing_caption_metadata(engine, plan, context):
    source = '1\n00:04:28,533 --> 00:04:29,333\nKuv muaj 2 tug me nyuam.'
    job = {'text': source, 'engine': engine, 'segment_plan': plan,
           'hmong_phrase_context': context, 'paragraph_pause': 0}
    assert ' '.join(segment.text for segment in plan_segments(job) if segment.text) == 'Kuv muaj ob tug me nyuam.'
    assert job['text'] == source


def test_f5_direct_adapter_verbalizes_target_without_changing_reference_words(monkeypatch):
    import numpy as np
    import hmong_assets
    import hmong_f5
    from hmong_engine import SpeechEngine

    engine = SpeechEngine()
    reference_path, _ = hmong_assets.reference('hmong-male')
    reference_words = 'Kuv muaj 2 tug.'
    captures = []

    def prepare(path, words, key):
        assert path == reference_path
        assert words == reference_words and key[-1] == reference_words
        return (np.ones((1, 4 * 24000), dtype=np.float32), 24000), words

    def infer(reference, words, text, model, **options):
        captures.append((words, text))
        return np.ones(24000, dtype=np.float32) * .1, 24000

    monkeypatch.setattr(engine, '_load', lambda quality: object())
    monkeypatch.setattr(engine, '_prepare_reference', prepare)
    monkeypatch.setattr(hmong_f5, 'infer_batch', infer)
    audio, rate = engine.synthesize('Kuv muaj 12 tug.', reference_path, reference_words)
    assert captures == [(reference_words, 'Kuv muaj kaum ob tug.')]
    assert rate == 24000 and len(audio) == 24000
