"""RPA text/pacing contracts; these do not score pronunciation or naturalness."""
import math

import pytest

from hmong_text import HmongTextError, estimate_new_seconds, iter_batches, normalize_text, syllable_count


def test_formatting_normalization_preserves_rpa_case_and_tone_suffixes():
    original = '\ufeff“Nyob\u00a0zoo…”\nPab\tPaj Pav Pas Pag Pam Pad Pa—Hmoob-Daw\u200b‘koj’'
    expected = '"Nyob zoo..." Pab Paj Pav Pas Pag Pam Pad Pa-Hmoob-Daw \'koj\''
    assert normalize_text(original) == expected
    assert normalize_text(expected) == expected
    assert normalize_text('b j v s g m d B J V S G M D') == 'b j v s g m d B J V S G M D'
    assert normalize_text('Kuv muaj 12345.67 nyiaj.') == 'Kuv muaj 12345.67 nyiaj.'
    assert normalize_text(' \t\r\n\u2003 ') == ''


@pytest.mark.parametrize('text', ['Tiếng Việt', '你好', '𖬀𖬰', '𞄀𞄁', 'Nyob\x00zoo', '🙂'])
def test_other_scripts_or_control_characters_are_not_silently_erased(text):
    with pytest.raises(HmongTextError, match='RPA'):
        normalize_text(text)


def test_optional_model_vocabulary_prevents_unknown_space_substitution():
    vocabulary = {'a': 0, 'b': 1, ' ': 2, '.': 3}
    assert normalize_text('a\u00a0b…', vocabulary=vocabulary) == 'a b...'
    with pytest.raises(HmongTextError, match='không tự thay'):
        normalize_text('a&b', vocabulary=vocabulary)


def test_syllables_count_rpa_units_not_english_letter_groups():
    assert syllable_count('Hmoob-Daw, Nyob zoo. Pab paj pav pas pag pam pad pa!') == 12
    assert syllable_count('Kuv muaj 12345.67 nyiaj.') == 4
    assert syllable_count('... - !!!') == 0


def test_reference_calibrated_duration_and_short_input_guard():
    # Four reference syllables in two seconds => two syllables per second.
    reference = 'Nyob zoo kuv tuaj.'
    target = 'Peb zoo siab heev.'
    assert estimate_new_seconds(reference, target, 2) == 2
    assert estimate_new_seconds(reference, target, 2, speed=.8) == 2.5
    assert estimate_new_seconds(reference, 'Nyob zoo.', 2) == pytest.approx(2 / 0.3 / 2)
    assert estimate_new_seconds(reference, 'Kuv.', 2) >= 1
    assert estimate_new_seconds(reference, target, .1) == 1


@pytest.mark.parametrize('seconds,speed', [(0, 1), (-1, 1), (math.inf, 1), (2, 0), (2, math.nan), (True, 1)])
def test_invalid_pacing_options_are_rejected(seconds, speed):
    with pytest.raises(HmongTextError):
        estimate_new_seconds('Nyob zoo.', 'Peb tuaj lawm.', seconds, speed)
    with pytest.raises(HmongTextError):
        estimate_new_seconds('...', 'Nyob zoo.', 2)


def test_batches_obey_both_bounds_without_losing_tone_letters_or_words():
    reference = 'Nyob zoo kuv tuaj.'
    text = ' '.join(['Pab paj pav pas pag pam pad pa.'] * 30)
    chunks = list(iter_batches(text, reference, 2, max_chars=140, max_new_seconds=12))
    assert len(chunks) > 1
    assert ' '.join(chunks) == text
    assert sum(syllable_count(chunk) for chunk in chunks) == syllable_count(text)
    assert all(len(chunk) <= 140 for chunk in chunks)
    assert all(estimate_new_seconds(reference, chunk, 2) <= 12 for chunk in chunks)
    # A slower selected pace creates more chunks, rather than exceeding context.
    slower = list(iter_batches(text, reference, 2, speed=.5, max_new_seconds=12))
    assert len(slower) > len(chunks)
    assert list(iter_batches('  ', reference, 2)) == []


def test_one_unspaced_token_is_not_cut_between_onset_vowel_and_tone_suffix():
    with pytest.raises(HmongTextError, match='dấu cách'):
        list(iter_batches('A' * 241, 'Nyob zoo kuv tuaj.', 2))


def test_batching_crosses_short_guard_threshold_before_rejecting_slow_reference():
    # A single word can exceed the budget at speed 0.3 while a complete phrase
    # fits after F5's ten-byte short-input guard switches off.
    chunks = list(iter_batches('Nyob tuaj.', 'Nyob zoo.', 12))
    assert chunks == ['Nyob tuaj.']
    assert estimate_new_seconds('Nyob zoo.', chunks[0], 12) == 12
