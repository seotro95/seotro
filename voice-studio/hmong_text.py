"""Conservative Hmong RPA normalization and reference-calibrated pacing.

RPA uses its final Latin letters as tone markers. They must never be removed,
romanized again or treated as English spelling. Duration here is a heuristic
based on whitespace/hyphen-separated syllables, not a pronunciation score.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
import math
import re
import string
import unicodedata


class HmongTextError(ValueError):
    """An actionable text or pacing error suitable for the user interface."""

    def __init__(self, message, *, unsupported_characters=()):
        super().__init__(message)
        self.unsupported_characters = list(dict.fromkeys(unsupported_characters))[:16]
        self.code = 'unsupported_speech_characters' if self.unsupported_characters else None


_TRANSLATION = str.maketrans({
    **{character: "'" for character in '‘’‚‛ʼ'},
    **{character: '"' for character in '“”„‟'},
    **{character: '-' for character in '‐‑‒–—―−'},
    '…': '...', '\u200b': ' ', '\ufeff': ' ',
})
_ALLOWED = frozenset(string.ascii_letters + string.digits + string.punctuation + ' ')
_SYLLABLE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*|[0-9]+(?:[.,][0-9]+)*")
_NUMERAL = re.compile(r'[0-9]+(?:[.,][0-9]+)*')
_DIGITS = ('xoom', 'ib', 'ob', 'peb', 'plaub', 'tsib', 'rau', 'xya', 'yim', 'cuaj')
_GROUPED_INTEGER = re.compile(r'[0-9]{1,3}([.,])[0-9]{3}(?:\1[0-9]{3})*')


def _shown(characters):
    return ', '.join(repr(character) for character in dict.fromkeys(characters))[:120]


def normalize_text(text: str, *, vocabulary: Collection[str] | Mapping[str, object] | None = None) -> str:
    """Normalize formatting only; preserve RPA letters, case and numeric text.

    Other scripts/diacritics are rejected rather than silently converted to the
    F5 vocabulary's unknown-space token. An optional vocabulary also checks
    model-specific ASCII punctuation. Empty formatting normalizes to ''.
    """
    if not isinstance(text, str):
        raise HmongTextError('Nội dung Hmong cần là văn bản.')
    normalized = unicodedata.normalize('NFC', text).translate(_TRANSLATION)
    normalized = ''.join(' ' if character.isspace() else character for character in normalized)
    normalized = re.sub(r' +', ' ', normalized).strip()
    unsupported = [character for character in normalized if character not in _ALLOWED]
    if unsupported:
        raise HmongTextError('Nội dung cần dùng chữ Hmong RPA (a–z), với chữ đuôi ghi thanh điệu. '
                             'Ký tự chưa hỗ trợ: ' + _shown(unsupported) + '. Không tự đổi hoặc bỏ chữ.',
                             unsupported_characters=unsupported)
    if vocabulary is not None:
        unknown = [character for character in normalized if character not in vocabulary]
        if unknown:
            raise HmongTextError('Mô hình không có các ký tự: ' + _shown(unknown)
                                 + '. Hãy sửa văn bản; tool không tự thay chúng bằng khoảng trắng.',
                                 unsupported_characters=unknown)
    return normalized


def _integer_words(digits: str) -> str:
    # Leading zeroes identify codes/phone-style fields, not a cardinal count.
    # Bound cardinal conversion independently of the length of a user script.
    if len(digits) > 9 or (len(digits) > 1 and digits.startswith('0')):
        return ' '.join(_DIGITS[int(digit)] for digit in digits)
    value = int(digits)
    if value < 10:
        return _DIGITS[value]
    if value < 100:
        tens, units = divmod(value, 10)
        head = 'kaum' if tens == 1 else 'nees nkaum' if tens == 2 else _DIGITS[tens] + ' caug'
        return head + (' ' + _DIGITS[units] if units else '')
    for scale, name in ((1_000_000, 'lab'), (1_000, 'txhiab'), (100, 'puas')):
        if value >= scale:
            count, remainder = divmod(value, scale)
            words = _integer_words(str(count)) + ' ' + name
            return words + (' ' + _integer_words(str(remainder)) if remainder else '')
    raise AssertionError('unreachable cardinal number')


def _numeral_words(token: str) -> str:
    if token.isdigit():
        return _integer_words(token)
    if _GROUPED_INTEGER.fullmatch(token):
        return _integer_words(token.replace('.', '').replace(',', ''))
    # A single separator is decimal unless it is a conventional triplet
    # grouping above. Mixed separators use the final one as the decimal mark;
    # the integer part must itself be a valid grouped integer.
    separator = max(token.rfind('.'), token.rfind(','))
    whole, fraction = token[:separator], token[separator + 1:]
    if whole.isdigit():
        integer = whole
    elif ('.' in token and ',' in token and _GROUPED_INTEGER.fullmatch(whole)
          and token[separator] not in whole):
        integer = whole.replace('.', '').replace(',', '')
    else:
        # Do not turn malformed numbers or IPv4 addresses into invented words.
        # The engine's normal vocabulary validation will report remaining digits.
        return token
    return _integer_words(integer) + token[separator] + ' ' + ' '.join(_DIGITS[int(digit)] for digit in fraction)


def normalize_speech_text(text: str) -> str:
    """Format Hmong target speech and verbalize standalone Arabic numerals.

    Source/reference normalization stays in ``normalize_text``. Whole counts
    up to nine digits use Hmong cardinal words; leading-zero identifiers and
    longer digit strings are read one digit at a time. A dot or comma between
    groups of exactly three digits denotes thousands. Otherwise a decimal
    separator remains punctuation and fractional digits are read individually.
    Existing RPA letters/case and unsupported alphanumeric tokens stay intact.
    Remove subtitle metadata before calling this target-speech formatter.
    """
    normalized = normalize_text(text)

    def replace(match):
        before = normalized[match.start() - 1] if match.start() else ''
        after = normalized[match.end()] if match.end() < len(normalized) else ''
        if before in {'+', '-'}:
            preceding = normalized[match.start() - 2] if match.start() > 1 else ''
            if not preceding or preceding.isspace() or preceding in '([,:;=':
                raise HmongTextError('Viết số có dấu + hoặc - bằng lời Hmong muốn đọc; '
                                     'tool chưa tự suy đoán cách đọc số âm.')
            if not preceding.isdigit():
                return match.group()
        if any(character and (character.isalnum() or character in '_/@') for character in (before, after)):
            return match.group()
        return _numeral_words(match.group())

    return _NUMERAL.sub(replace, normalized)


def syllable_count(text: str) -> int:
    """Count RPA orthographic syllables, including hyphen-separated units.

    Digits remain opaque input units; this does not guess Hmong number words.
    Borrowed words/proper names may not follow the monosyllabic RPA heuristic.
    """
    return len(_SYLLABLE.findall(normalize_text(text)))


def estimate_new_seconds(reference_text: str, text: str, reference_seconds: float, speed: float = 1.0) -> float:
    """Estimate generated duration from the actual reference syllable rate.

    Retain F5's short-input guard: below ten UTF-8 bytes its local speed is 0.3.
    One second is a floor so a short utterance is not forced into a tiny mel.
    """
    for value, label in ((reference_seconds, 'Thời lượng mẫu'), (speed, 'Tốc độ')):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise HmongTextError(label + ' cần là số dương hữu hạn.')
    reference = normalize_text(reference_text)
    target = normalize_text(text)
    reference_count, target_count = syllable_count(reference), syllable_count(target)
    if not reference_count or not target_count:
        raise HmongTextError('Lời mẫu và nội dung cần có từ Hmong RPA, không chỉ dấu câu hoặc khoảng trắng.')
    local_speed = 0.3 if len(target.encode('utf-8')) < 10 else speed
    return max(1.0, float(reference_seconds) * target_count / reference_count / local_speed)


def iter_batches(text: str, reference_text: str, reference_seconds: float, speed: float = 1.0,
                 *, max_chars: int = 240, max_new_seconds: float = 16.0):
    """Yield whole-word chunks within both character and estimated time bounds.

    A single oversized unspaced token is rejected instead of splitting its RPA
    tone suffix. Whitespace is normalized, while all words/punctuation survive.
    """
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise HmongTextError('Giới hạn ký tự cần là số nguyên dương.')
    if (isinstance(max_new_seconds, bool) or not isinstance(max_new_seconds, (int, float))
            or not math.isfinite(max_new_seconds) or max_new_seconds < 1):
        raise HmongTextError('Giới hạn thời lượng đoạn cần ít nhất một giây.')
    normalized = normalize_text(text)
    if not normalized:
        return
    # Validate the reference and numeric options even before the first chunk.
    estimate_new_seconds(reference_text, normalized, reference_seconds, speed)

    tokens = normalized.split(' ')
    start = 0
    while start < len(tokens):
        candidate = ''
        accepted = ''
        next_start = start
        for index in range(start, len(tokens)):
            candidate += (' ' if candidate else '') + tokens[index]
            if len(candidate) > max_chars:
                break
            if not syllable_count(candidate):
                continue
            if estimate_new_seconds(reference_text, candidate, reference_seconds, speed) <= max_new_seconds:
                accepted = candidate
                next_start = index + 1
            # Adding text can lower duration when the short-input speed guard
            # turns off at ten bytes. After that point duration is monotonic.
            elif len(candidate.encode('utf-8')) >= 10:
                break
        if not accepted:
            raise HmongTextError('Một từ hoặc cụm không có dấu cách vượt giới hạn tạo giọng. '
                                 'Thêm dấu cách đúng giữa các âm tiết và kiểm tra lời mẫu khớp bản thu.')
        yield accepted
        start = next_start
