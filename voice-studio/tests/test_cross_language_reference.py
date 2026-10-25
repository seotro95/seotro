"""Native speaker identity uses selected audio; F5 still needs matching words."""
import pytest

from hmong_reference import ReferenceError, describe_reference, select_reference


@pytest.mark.parametrize('words', ['', 'Xin chào các bạn.', '你好，这是一段录音。'])
def test_native_custom_reference_accepts_optional_original_language_words(words):
    content = b'unknown selected voice upload'
    info = describe_reference(content, 6, require_transcript=False)
    assert info['requires_transcript'] is False
    assert info['cross_language_reference'] is True
    assert info['reference_conditioning'] == 'audio'
    selected = select_reference(content, 6, words, require_transcript=False)
    assert selected['transcript'] == words
    assert selected['known_preset'] is None
    assert selected['reference_start'] == 0 and selected['reference_end'] == 6
    assert selected['cross_language_reference'] and selected['reference_conditioning'] == 'audio'


def test_native_foreign_reference_long_upload_still_requires_real_crop():
    content = b'unknown external long upload'
    assert describe_reference(content, 20, require_transcript=False)['requires_selection']
    with pytest.raises(ReferenceError, match='3–8'):
        select_reference(content, 20, '', require_transcript=False)
    selection = select_reference(content, 20, '', 4, 11, require_transcript=False)
    assert selection['reference_start'] == 4 and selection['reference_end'] == 11
    for start, end in [(0, 2), (0, 9), (18, 22), (True, 6)]:
        with pytest.raises(ReferenceError):
            select_reference(content, 20, '', start, end, require_transcript=False)


def test_f5_still_requires_matching_reference_words_by_default():
    assert describe_reference(b'unknown F5 voice', 6)['requires_transcript']
    with pytest.raises(ReferenceError, match='đúng lời Hmong'):
        select_reference(b'unknown F5 voice', 6, '')


@pytest.mark.parametrize('words', [None, [], 'x' * 2001])
def test_native_optional_transcript_still_rejects_invalid_metadata(words):
    with pytest.raises(ReferenceError):
        select_reference(b'unknown native voice', 6, words, require_transcript=False)


def test_native_known_preset_prefill_is_kept_and_does_not_replace_custom_words():
    from hmong_assets import ROOT, references
    item = references()['female']
    content = (ROOT / item['file']).read_bytes()
    automatic = select_reference(content, item['duration'], '', require_transcript=False)
    assert automatic['transcript'] == item['reference']['text']
    assert automatic['automatic_reference']
    foreign = 'Xin chào, đây là giọng của tôi.'
    selected = select_reference(content, item['duration'], foreign, require_transcript=False)
    assert selected['transcript'] == foreign and not selected['automatic_reference']
